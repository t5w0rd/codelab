package tutils

import (
    "net"
    "bytes"
    "encoding/binary"
    "sync"
    "errors"
    "io"
    "flag"
)

/* encrypt connection
===================================
conn \                       / conn
conn -<-> proxy <-> agent <->- conn
conn /                       \ conn
===================================
*/

const cmd_connect uint16 = 0
const cmd_data uint16 = 1
const cmd_close uint16 = 2

const server_mode_proxy = 0
const server_mode_agent = 1



type connChanItem struct {
    cmd uint16
    reader io.Reader
}

type EncryptTunPeer struct {
    // 所有线程都有用到，初始化后不会改动 或 线程安全
    connMap *sync.Map
    peer *net.TCPConn
    addr *net.TCPAddr
    mode byte
    connChanMap *sync.Map  // map[uint32] chan connChanItem

    // 只有主线程用到
    preConnChan chan connChanItem // 预创建的 chan，用于 connChanMap.LoadOrStore
}

type EncryptTunConnection struct {
    conn *net.TCPConn
    peer *EncryptTunPeer
    connId uint32
}

func NewEncryptTunProxy(peer *net.TCPConn, laddr string) (obj *EncryptTunPeer) {
    obj = new(EncryptTunPeer)
    obj.connMap = new(sync.Map)
    obj.peer = peer
    obj.addr, _ = net.ResolveTCPAddr("tcp", laddr)
    obj.mode = server_mode_proxy
    obj.connChanMap = new(sync.Map)
    obj.preConnChan = make(chan connChanItem)
    return obj
}

// 创建连接对象
func (self *EncryptTunPeer) newEncryptTunConnection(conn *net.TCPConn, connId uint32) (obj *EncryptTunConnection) {
    obj = new(EncryptTunConnection)
    obj.connId = connId
    obj.peer = self
    if conn != nil {
        obj.conn = conn
        self.connMap.Store(connId, obj)
    }
    return obj
}

// connect = cmd:uint16 + connId:uint32
func packConnect(connId uint32) (ret []byte) {
    payload := bytes.NewBuffer([]byte{})
    binary.Write(payload, binary.BigEndian, cmd_connect)
    binary.Write(payload, binary.BigEndian, connId)
    ret = NewSldeWithData(payload.Bytes()).Bytes()
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
    return ret
}

// close cmd:uint16 + connId:uint32
func packClose(connId uint32) (ret []byte) {
    payload := bytes.NewBuffer([]byte{})
    binary.Write(payload, binary.BigEndian, cmd_close)
    binary.Write(payload, binary.BigEndian, connId)
    ret = NewSldeWithData(payload.Bytes()).Bytes()
    return ret
}

// 连接处理循环
func (self *EncryptTunPeer) goStartConnHandler(conn *net.TCPConn, connId uint32) {
    go func() {
        buf := make([]byte, 0xffff)
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
            protodata := packData(connId, buf[:n])
            self.peer.Write(protodata)
        }
        //protodata := packClose(connId)
        //self.peer.Write(protodata)
    }()
}

// 解码出 cmd 并且返回一个用于继续解码的 io.Reader
func unpackCmd(data []byte) (cmd uint16, reader io.Reader) {
    reader = bytes.NewBuffer([]byte{})
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

func (self *EncryptTunPeer) clear() {
    self.connMap.Range(func (key, value interface{}) bool {
        econn := value.(*EncryptTunConnection)
        econn.conn.Close()
        return true
    })
    self.connMap = new(sync.Map)
}

// 处理远端 peer 发送过来的请求
func (self *EncryptTunPeer) goStartPeerConnOpHandler(conn *net.TCPConn, connId uint32) (connChan chan connChanItem) {
    connChan = make(chan connChanItem)
    self.connChanMap.Store(connId, connChan)

    go func () {
        for {
            item, ok := <-connChan
            if !ok {
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
                }

            case cmd_data:
                data := unpackData(item.reader)
                conn.Write(data)
            case cmd_close:
                unpackClose(item.reader)
                conn.Close()  // !!!!!!
                break
            }
        }
    }()

    return connChan
}

// 连接操作序列化
func (self *EncryptTunPeer) dispatchPeerConnOp(cmd uint16, reader io.Reader) {
    connId := unpackConnId(reader)
    var connChan chan connChanItem
    if cmd == cmd_connect {
        connChan = self.goStartPeerConnOpHandler(nil, connId)
    } else {
        if v, ok := self.connChanMap.Load(connId); ok {
            connChan = v.(chan connChanItem)
        }
    }
    connChan <- connChanItem{cmd, reader}
}

// 主连接处理循环
func (self *EncryptTunPeer) goStartPeerHandler() {
    go func() {
        buf := make([]byte, 0xffff)
        slde := NewSlde()
        sldeleft := SLDE_HEADER_SIZE
        for {
            n, err := self.peer.Read(buf)
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

                cmd, recvReader := unpackCmd(recvdata)
                switch cmd {
                case cmd_connect:
                    self.dispatchPeerConnOp(cmd, recvReader)
                case cmd_data:
                    self.dispatchPeerConnOp(cmd, recvReader)
                case cmd_close:
                    self.dispatchPeerConnOp(cmd, recvReader)
                }
                /*
                iconn, _ := self.connMap.Load(connId)
                data := unpackData(recvReader)
                if econn == nil {
                    if self.mode == server_mode_proxy {
                        // connId 错误
                        println("Wrong connId")
                    } else if self.mode == server_mode_agent {
                        if cmd == cmd_data {
                            // 新的连接
                            go self.agentConnect(connId, data)
                        }
                    }
                }

                self.peer.Write(data)
            case cmd_close:
                if econn == nil {
                    // 可能是 proxy 端的连接没有发送过数据就
                    println("Wrong connId")
                } else {
                    // 关闭连接
                    unpackClose(recvReader)
                    econn.conn.Close()
                    self.connMap.Delete(connId)
                }
                */
            }
        }
    }()
}

func (self *EncryptTunPeer) startProxy() (err error) {
    lstn, err := net.ListenTCP("tcp", self.addr)
    if err != nil {
        println(err.Error())
        return err
    }
    defer lstn.Close()

    self.goStartPeerHandler()

    var connId uint32 = 0
    for {
        conn, err := lstn.AcceptTCP()
        if err != nil {
            println(err.Error())
            continue
        }

        connId += 1
        self.goStartPeerConnOpHandler(conn, connId)
        data := packConnect(connId)
        self.peer.Write(data)
        self.goStartConnHandler(conn, connId)
    }
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

func NewEncryptTunAgent(peer *net.TCPConn, raddr string) (obj *EncryptTunPeer) {
    obj = new(EncryptTunPeer)
    obj.connMap = new(sync.Map)
    obj.peer = peer
    obj.addr, _ = net.ResolveTCPAddr("tcp", raddr)
    obj.mode = server_mode_agent
    return obj
}

func (self *EncryptTunPeer) startAgent() (err error) {
    return nil
}