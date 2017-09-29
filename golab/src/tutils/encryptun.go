package tutils

import (
	"net"
	"bytes"
	"encoding/binary"
	"sync"
)

type connMapSync struct {
	sync.RWMutex
	connMap map[uint32] *net.TCPConn
}

type rRangeCallback func (key uint32, value *net.TCPConn)

func (self *connMapSync) Get(key uint32) (value *net.TCPConn, ok bool) {
	self.RLock()
	value, ok = self.connMap[key]
	self.RUnlock()
	return
}

func (self *connMapSync) Set(key uint32, value *net.TCPConn) {
	self.Lock()
	self.connMap[key] = value
	self.Unlock()
}

func (self *connMapSync) Delete(key uint32) {
	self.Lock()
	delete(self.connMap, key)
	self.Unlock()
}

func (self *connMapSync) RRange(callback rRangeCallback) {
	self.RLock()
	for key, value := range self.connMap {
		callback(key, value)
	}
	self.RUnlock()
}

func newConnMapSync() (obj *connMapSync) {
	obj = new(connMapSync)
	obj.connMap = make(map[uint32] *net.TCPConn)
	return
}

const cmd_data uint16 = 1
const cmd_close uint16 = 2

//type ProtoData struct {
//  cmd uint32
//	clientId uint32
//  dataLen uint32
//	data []byte
//}

//type ProtoClose struct {
//  cmd uint32
//	clientId uint32
//}

func packData(connId uint32, data []byte) (ret []byte) {
	payload := bytes.NewBuffer([]byte{})
	binary.Write(payload, binary.BigEndian, cmd_data)
	binary.Write(payload, binary.BigEndian, connId)
	dataLen := uint32(len(data))
	binary.Write(payload, binary.BigEndian, dataLen)
	binary.Write(payload, binary.BigEndian, data)
	ret = NewSldeWithData(payload.Bytes()).Bytes()
	return
}

func packClose(connId uint32) (ret []byte) {
	payload := bytes.NewBuffer([]byte{})
	binary.Write(payload, binary.BigEndian, cmd_close)
	binary.Write(payload, binary.BigEndian, connId)
	ret = NewSldeWithData(payload.Bytes()).Bytes()
	return
}

func unpackCmd(data []byte) (cmd uint16, payload *bytes.Buffer) {
	payload = bytes.NewBuffer([]byte{})
	binary.Read(payload, binary.BigEndian, &cmd)
	return
}

func unpackData(payload *bytes.Buffer) (connId uint32, data []byte) {
	binary.Read(payload, binary.BigEndian, &connId)
	var dataLen uint32
	binary.Read(payload, binary.BigEndian, &dataLen)
	data = make([]byte, dataLen)
	binary.Read(payload, binary.BigEndian, data)
	return
}

func unpackClose(payload *bytes.Buffer) (connId uint32) {
	binary.Read(payload, binary.BigEndian, &connId)
	return
}

func proxyConnHandler(peer *net.TCPConn, conn *net.TCPConn, connId uint32) {
	defer conn.Close()
	firstData := true
	buf := make([]byte, 0xffff)
	for {
		n, err := conn.Read(buf)
		if err != nil || n <= 0 {
			if !firstData {
				// tell to close
				protodata := packClose(connId)
				peer.Write(protodata)
			}
			return
		}

		// tell to (connect and )send data
		protodata := packData(connId, buf[:n])
		peer.Write(protodata)
	}
}

func proxyPeerHandler(peer *net.TCPConn, connMap *connMapSync) {
	buf := make([]byte, 0xffff)
	slde := NewSlde()
	sldeleft := SLDE_HEADER_SIZE
	for {
		n, err := peer.Read(buf)
		if err != nil || n <= 0 {
			if err != nil {
				println(err.Error())
			} else {
				println("remote peer closed")
			}
			// TODO: close all connection
			return
		}

		sldeleft, err = slde.Write(buf[:n])
		if err != nil {
			println(err.Error())
			// TODO: close all connection
			return
		}

		if sldeleft == 0 {
			// a slde recieve finished
			payloaddata, err := slde.Decode()
			if err != nil {
				println(err.Error())
				// TODO: close all connection
				return
			}

			cmd, payload := unpackCmd(payloaddata)
			var connId uint32
			switch cmd {
			case cmd_data:
				var data []byte
				connId, data = unpackData(payload)
				if conn, ok := connMap.Get(connId); ok {
					conn.Write(data)
				}
			case cmd_close:
				connId = unpackClose(payload)
				if conn, ok := connMap.Get(connId); ok {
					// close connection
					conn.Close()
					connMap.Delete(connId)
				}
			}
		}
	}
}


func EncryptProxy(peer *net.TCPConn, laddr string) {
	tcpAddr, err := net.ResolveTCPAddr("tcp", laddr)
	if err != nil {
		println(err.Error())
		return
	}

	lstn, err := net.ListenTCP("tcp", tcpAddr)
	if err != nil {
		println(err.Error())
		return
	}
	defer lstn.Close()

	connMap := newConnMapSync()
	var connIdGen uint32 = 0
	go proxyPeerHandler(peer, connMap)
	for {
		conn, err := lstn.AcceptTCP()
		if err != nil {
			// TODO: close all connections
			println(err.Error())
			return
		}
		connIdGen += 1
		connMap.Set(connIdGen, conn)
		go proxyConnHandler(peer, conn, connIdGen)
	}
}

func agentConnHandler(peer *net.TCPConn, connMap *connMapSync, tcpAddr *net.TCPAddr, data []byte, connId uint32) {
	conn, err := net.DialTCP("tcp", nil, tcpAddr)
	if err != nil {
		// tell to close
		protodata := packClose(connId)
		peer.Write(protodata)
		return
	}
	connMap.Set(connId, conn)

	conn.Write(data)
}

func EncryptAgent(peer *net.TCPConn, raddr string) {
	tcpAddr, err := net.ResolveTCPAddr("tcp", raddr)
	if err != nil {
		println(err.Error())
		return
	}

	connMap := newConnMapSync()

	buf := make([]byte, 0xffff)
	slde := NewSlde()
	sldeleft := SLDE_HEADER_SIZE
	for {
		n, err := peer.Read(buf[:sldeleft])
		if err != nil || n <= 0 {
			if err != nil {
				println(err.Error())
			} else {
				println("remote peer closed")
			}
			// TODO: close all connection
			return
		}

		sldeleft, err = slde.Write(buf[:n])
		if err != nil {
			println(err.Error())
			// TODO: close all connection
			return
		}

		if sldeleft == 0 {
			// a slde recieve finished
			payloaddata, err := slde.Decode()
			if err != nil {
				println(err.Error())
				// TODO: close all connection
				return
			}

			cmd, payload := unpackCmd(payloaddata)
			var connId uint32
			switch cmd {
			case cmd_data:
				var data []byte
				connId, data = unpackData(payload)
				if conn, ok := connMap.Get(connId); ok {
					conn.Write(data)
				} else {
					// connect
					go agentConnHandler(peer, connMap, tcpAddr, data, connId)
				}
			case cmd_close:
				connId = unpackClose(payload)
				if conn, ok := connMap.Get(connId); ok {
					// close connection
					conn.Close()
					connMap.Delete(connId)
				}
			}
		}
	}
}