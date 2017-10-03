package tutils

import (
    "net"
    "bytes"
    "encoding/binary"
    "sync"
    "errors"
    "io"
    "log"
)

/* encrypt connection
===================================
conn \                       / conn
conn -<-> proxy <-> agent <->- conn
conn /                       \ conn
===================================
*/

const (
    cmd_connect uint16 = 0
    cmd_data uint16 = 1
    cmd_close uint16 = 2

    server_mode_proxy = 0
    server_mode_agent = 1

    max_tcp_read               = 0xffff
    max_peer_conn_op_chan_size = 10
    max_close_notify_chan_size = 1024
)


type connChanItem struct {
    cmd uint16
    reader io.Reader
}

type EncryptTunPeer struct {
    // 所有线程都有用到，初始化后不会改动 或 线程安全
    peer *net.TCPConn
    addr *net.TCPAddr
    mode byte
    connChanMap *sync.Map  // map[uint32] chan connChanItem
    connCloseNotifyChan chan chan connChanItem
    lstn *net.TCPListener
}

func NewEncryptTunProxy(peer *net.TCPConn, laddr string) (obj *EncryptTunPeer) {
    obj = new(EncryptTunPeer)
    obj.peer = peer
    obj.addr, _ = net.ResolveTCPAddr("tcp", laddr)
    obj.mode = server_mode_proxy
    obj.connChanMap = new(sync.Map)
    obj.connCloseNotifyChan = make(chan chan connChanItem, max_close_notify_chan_size)
    return obj
}

func NewEncryptTunAgent(peer *net.TCPConn, raddr string) (obj *EncryptTunPeer) {
    obj = new(EncryptTunPeer)
    obj.peer = peer
    obj.addr, _ = net.ResolveTCPAddr("tcp", raddr)
    obj.mode = server_mode_agent
    obj.connChanMap = new(sync.Map)
    obj.connCloseNotifyChan = make(chan chan connChanItem, max_close_notify_chan_size)
    return obj
}

// connect = cmd:uint16 + connId:uint32
func packConnect(connId uint32) (ret []byte) {
    payload := bytes.NewBuffer([]byte{})
    binary.Write(payload, binary.BigEndian, cmd_connect)
    binary.Write(payload, binary.BigEndian, connId)
    ret = NewSldeWithData(payload.Bytes()).Bytes()
    //log.Println("pack", ret)
    return ret
}

// write = cmd:uint16 + connId:uint32 + dataLen:uint32 + data:string(dataLen)
func packData(connId uint32, data []byte) (ret []byte) {
    payload := bytes.NewBuffer([]byte{})
    binary.Write(payload, binary.BigEndian, cmd_data)
    binary.Write(payload, binary.BigEndian, connId)
    dataLen := uint32(len(data))
    binary.Write(payload, binary.BigEndian, dataLen)
    binary.Write(payload, binary.BigEndian, data)
    ret = NewSldeWithData(payload.Bytes()).Bytes()
    //log.Println("pack", ret)
    return ret
}

// close cmd:uint16 + connId:uint32
func packClose(connId uint32) (ret []byte) {
    payload := bytes.NewBuffer([]byte{})
    binary.Write(payload, binary.BigEndian, cmd_close)
    binary.Write(payload, binary.BigEndian, connId)
    ret = NewSldeWithData(payload.Bytes()).Bytes()
    //log.Println("pack", ret)
    return ret
}

// 解码出 cmd 并且返回一个用于继续解码的 io.Reader
func unpackCmd(data []byte) (cmd uint16, reader io.Reader) {
    reader = bytes.NewBuffer(data)
    binary.Read(reader, binary.BigEndian, &cmd)
    return cmd, reader
}

// 解码 connId
func unpackConnId(reader io.Reader) (connId uint32) {
    binary.Read(reader, binary.BigEndian, &connId)
    return connId
}

func unpackConnect(reader io.Reader) {
}

func unpackData(reader io.Reader) (data []byte) {
    var dataLen uint32
    binary.Read(reader, binary.BigEndian, &dataLen)
    data = make([]byte, dataLen)
    binary.Read(reader, binary.BigEndian, data)
    return data
}

func unpackClose(reader io.Reader) {
}

func (self *EncryptTunPeer) notifyToCloseChan(c chan connChanItem) {
    for {
        select {
        case <-c:
            <-c  // drop
        default:
            self.connCloseNotifyChan <- c
            println("@@@@@@!!!!!@@@@@")
            return
        }
    }
}

func (self *EncryptTunPeer) clear() {
    log.Println("clear")
    self.connChanMap.Range(func (k, v interface{}) bool {
        connId := k.(uint32)
        connChan := v.(chan connChanItem)
        log.Printf("clear, close conn(%d) chan\n", connId)
        close(connChan)
        return true
    })
}

// 连接处理循环
func (self *EncryptTunPeer) startConnHandler(conn *net.TCPConn, connId uint32) {
    log.Printf("start conn(%d) handler\n", connId)
    buf := make([]byte, max_tcp_read)
    for {
        n, err := conn.Read(buf)
        if err != nil {
            println(err.Error())
            break
        }
        if n <= 0 {
            err = errors.New("Connection is closed")
            println(err.Error())
            break
        }

        // tell to (connect and )send data
        log.Println("op: senddata")
        protodata := packData(connId, buf[:n])
        self.peer.Write(protodata)
    }

    log.Printf("stop conn(%d) handler\n", connId)
    if v, ok := self.connChanMap.Load(connId); ok {
        // 来自 conn 的关闭
        log.Println("op: close")
        protodata := packClose(connId)
        self.peer.Write(protodata)
        connChan := v.(chan connChanItem)
        log.Printf("conn EOF, notify to close conn(%d) chan\n", connId)
        //safeClose(connChan)
        self.notifyToCloseChan(connChan)
    }
}

// 处理远端 peer 发送过来的请求
func (self *EncryptTunPeer) goStartPeerConnOpHandler(conn *net.TCPConn, connId uint32) (connChan chan connChanItem) {
    log.Printf("start peer conn(%d) op handler\n", connId)
    connChan = make(chan connChanItem, max_peer_conn_op_chan_size)
    self.connChanMap.Store(connId, connChan)

    go func () {
        var ok bool
        var item connChanItem
        for {
            item, ok = <-connChan
            if !ok {
                log.Printf("conn(%d) chan is closed\n", connId)
                self.connChanMap.Delete(connId)
                if conn != nil {
                    conn.Close()
                }
                break
            }

            switch item.cmd {
            case cmd_connect:
                unpackConnect(item.reader)
                // agent
                var err error
                conn, err = net.DialTCP("tcp", nil, self.addr)
                if err != nil {
                    // tell to close
                    println(err.Error())
                    protodata := packClose(connId)
                    self.peer.Write(protodata)
                    log.Printf("dial err, notify to close conn(%d) chan\n", connId)
                    //safeClose(connChan)
                    self.notifyToCloseChan(connChan)
                } else {
                    go self.startConnHandler(conn, connId)
                }

            case cmd_data:
                data := unpackData(item.reader)
                conn.Write(data)
            case cmd_close:
                unpackClose(item.reader)
                self.connChanMap.Delete(connId)
                conn.Close()
                log.Printf("peer op, notify to close conn(%d) chan\n", connId)
                //safeClose(connChan)
                self.notifyToCloseChan(connChan)
                break
            }
        }
        log.Printf("stop peer conn(%d) op handler\n", connId)
    }()

    return connChan
}

// 连接操作序列化
func (self *EncryptTunPeer) dispatchPeerConnOp(cmd uint16, reader io.Reader) {
    connId := unpackConnId(reader)
    var connChan chan connChanItem
    if cmd == cmd_connect {
        connChan = self.goStartPeerConnOpHandler(nil, connId)
    } else if v, ok := self.connChanMap.Load(connId); ok {
        connChan = v.(chan connChanItem)
    } else {
        log.Printf("!!closed connId(%d)\n", connId)
        return
    }
    println(connId, "@@send conn chan")
    connChan <- connChanItem{cmd, reader}
    println(connId, "##send conn chan<-")
}

// 主连接处理循环
func (self *EncryptTunPeer) startPeerHandler() {
    log.Println("start peer handler")
    buf := make([]byte, max_tcp_read)
    slde := NewSlde()
    sldeleft := SLDE_HEADER_SIZE
    for {
        log.Printf("peer will read %d bytes\n", sldeleft)
        println("@@@@@@@@@@@@@@@@")
        n, err := self.peer.Read(buf[:sldeleft])
        if err != nil {
            println(err.Error())
            // close all connection
            self.clear()
            break
        }

        if n <= 0 {
            err = errors.New("Remote peer closed")
            println(err.Error())
            // close all connection
            self.clear()
            break
        }
        println("###############")

        sldeleft, err = slde.Write(buf[:n])
        if err != nil {
            println(err.Error())
            // close all connection
            self.clear()
            break
        }

        if sldeleft == 0 {
            // 一个协议包接收完成，根据connId将slde加入对应的待处理队列
            recvdata, err := slde.Decode()
            if err != nil {
                println(err.Error())
                // close all connection
                self.clear()
                break
            }
            slde = NewSlde()
            sldeleft = SLDE_HEADER_SIZE
            log.Println("slde recv complete")

            select {
            case <-self.connCloseNotifyChan:
                if connChan, ok := <-self.connCloseNotifyChan; ok {
                    log.Println("close conn chan", connChan)
                    close(connChan)
                }
            default:
            }

            cmd, recvReader := unpackCmd(recvdata)
            switch cmd {
            case cmd_connect:
                log.Println("dispatch cmd: connect")
                self.dispatchPeerConnOp(cmd, recvReader)
            case cmd_data:
                log.Println("dispatch cmd: senddata")
                self.dispatchPeerConnOp(cmd, recvReader)
            case cmd_close:
                log.Println("dispatch cmd: close")
                self.dispatchPeerConnOp(cmd, recvReader)
            }
        } else if sldeleft > max_tcp_read {
            sldeleft = max_tcp_read
        }
    }

    if self.mode == server_mode_proxy {
        self.lstn.Close()
    }
    log.Println("stop peer handler")
}

func (self *EncryptTunPeer) startProxy() (err error) {
    log.Println("proxy is starting")
    self.lstn, err = net.ListenTCP("tcp", self.addr)
    if err != nil {
        println(err.Error())
        return err
    }
    defer self.lstn.Close()

    go self.startPeerHandler()

    var connId uint32 = 0
    for {
        conn, err := self.lstn.AcceptTCP()
        if err != nil {
            println(err.Error())
            break
        }

        connId += 1
        self.goStartPeerConnOpHandler(conn, connId)
        log.Println("op: connect")
        data := packConnect(connId)
        self.peer.Write(data)
        go self.startConnHandler(conn, connId)
    }

    return err
}

func (self *EncryptTunPeer) startAgent() (err error) {
    log.Println("agent is starting")
    self.startPeerHandler()
    return nil
}

// 启动proxy
func (self *EncryptTunPeer) Start() (err error) {
    if self.mode == server_mode_proxy {
        return self.startProxy()
    } else if self.mode == server_mode_agent {
        return self.startAgent()
    }

    err = errors.New("Unsupported mode")
    return err
}
