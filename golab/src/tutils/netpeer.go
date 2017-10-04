package tutils

import (
	"log"
	"net"
	"sync"
	"time"
)

const (
	read_buf_size int = 0xffff
)

type TCPConnEx struct {
	net.TCPConn
	ReadSize int
	Ext      interface{}
}

type TcpServer struct {
	lstn        *net.TCPListener
	Addr        string
	ConnMap     *sync.Map
	connWg      sync.WaitGroup
	ReadBufSize int

	Ext interface{}

	// Listener 监听成功后调用，如果返回 err != nil 则服务器会退出
	OnListenSuccCallback func(self *TcpServer) (err error)

	// 有新连接接入后调用，返回值意义如下：
	// ok: 如果为 false 该连接将会关闭
	// ReadSize: conn 希望连接读取的字节数，如果设置为0，则不会提供一个 self.connReadHandler 例程来读取数据，也就是说可以在 OnAcceptConnCallback 中自定义处理例程
	// connExt: 为 conn 扩展的字段，将会传递到 TCPConnEx 结构中
	OnAcceptConnCallback func(self *TcpServer, conn *net.TCPConn, connId uint32) (ok bool, readSize int, connExt interface{})

	// 连接收到数据后调用，len(data) <= conn.ReadSize，可以在回调中重新设置 conn.ReadSize 来调整下一次期望收到数据的长度
	// 返回值 ok 为 false 将清理并关闭该连接
	OnHandleConnDataCallback func(self *TcpServer, conn *TCPConnEx, connId uint32, data []byte) (ok bool)

	// 关闭连接时调用
	OnCloseConnCallback func(self *TcpServer, conn *TCPConnEx, connId uint32)
}

func NewTcpServer() (obj *TcpServer) {
	obj = new(TcpServer)
	obj.ConnMap = new(sync.Map)
	obj.ReadBufSize = read_buf_size
	return obj
}

func (self *TcpServer) connReadHandler(conn *TCPConnEx, connId uint32) {
	defer func() {
		if self.OnCloseConnCallback != nil {
			self.OnCloseConnCallback(self, conn, connId)
		}
		self.ConnMap.Delete(connId)
		conn.Close()
		self.connWg.Done()
	}()

	buf := make([]byte, self.ReadBufSize)
	for {
		n, err := conn.Read(buf[:conn.ReadSize])
		if err != nil {
			log.Printf("conn(%d), %s\n", connId, err.Error())
			break
		}

		data := buf[:n]
		if self.OnHandleConnDataCallback != nil && !self.OnHandleConnDataCallback(self, conn, connId, data) {
			break
		}
	}
}

func (self *TcpServer) Start() (err error) {
	addr, err := net.ResolveTCPAddr("tcp", self.Addr)
	if err != nil {
		log.Println(err.Error())
		return err
	}

	self.lstn, err = net.ListenTCP("tcp", addr)
	if err != nil {
		log.Println(err.Error())
		return err
	}
	defer self.lstn.Close()
	if self.OnListenSuccCallback != nil {
		if err = self.OnListenSuccCallback(self); err != nil {
			return err
		}
	}

	var connId uint32 = 0
	for {
		conn, err := self.lstn.AcceptTCP()
		if err != nil {
			log.Println(err.Error())
			return err
		}

		connId++
		if self.OnAcceptConnCallback != nil {
			if ok, readSize, ext := self.OnAcceptConnCallback(self, conn, connId); ok {
				connx := &TCPConnEx{*conn, readSize, ext}
				self.ConnMap.Store(connId, connx)
				self.connWg.Add(1)
				if readSize > 0 {
					// readSize > 0 的时候走正常处理函数
					go self.connReadHandler(connx, connId)
				}
			} else {
				connId--
				conn.Close()
			}
		} else {
			connx := &TCPConnEx{*conn, self.ReadBufSize, nil}
			self.ConnMap.Store(connId, connx)
			self.connWg.Add(1)
			go self.connReadHandler(connx, connId)
		}
	}
	return nil
}

type TcpClient struct {
	Addr        string
	RetryDelay  time.Duration // >= 0
	MaxRetry    int           // -1: infine; 0: no retry
	ReadBufSize int

	Ext interface{}

	// 连接成功后调用，返回值意义如下
	// ok: 如果为 false 该连接将会关闭
	// ReadSize: conn 希望连接读取的字节数
	// connExt: 为 conn 扩展的字段，将会传递到 TCPConnEx 结构中
	OnDialCallback func(self *TcpClient, conn *net.TCPConn) (ok bool, readSize int, connExt interface{})

	OnHandleConnDataCallback func(self *TcpClient, conn *TCPConnEx, data []byte) (ok bool)

	// 关闭连接时调用
	OnCloseConnCallback func(self *TcpClient, conn *TCPConnEx)
}

func NewTcpClient() (obj *TcpClient) {
	obj = new(TcpClient)
	obj.RetryDelay = 0
	obj.MaxRetry = 0
	obj.ReadBufSize = read_buf_size
	return obj
}

func (self *TcpClient) connReadHandler(conn *TCPConnEx) {
	defer func() {
		if self.OnCloseConnCallback != nil {
			self.OnCloseConnCallback(self, conn)
		}
		conn.Close()
	}()

	buf := make([]byte, self.ReadBufSize)
	for {
		n, err := conn.Read(buf[:conn.ReadSize])
		if err != nil {
			log.Printf("%s\n", err.Error())
			break
		}

		data := buf[:n]
		if self.OnHandleConnDataCallback != nil && !self.OnHandleConnDataCallback(self, conn, data) {
			break
		}
	}
}

func (self *TcpClient) Start() (err error) {
	addr, err := net.ResolveTCPAddr("tcp", self.Addr)
	if err != nil {
		log.Println(err.Error())
		return err
	}

	retryTimes := self.MaxRetry
	for {
		tm := time.Now()
		conn, err := net.DialTCP("tcp", nil, addr)
		if err != nil {
			log.Println(err.Error())
			if retryTimes == 0 {
				break
			} else if retryTimes > 0 {
				retryTimes--
			}

			left := self.RetryDelay - time.Now().Sub(tm)
			if left > 0 {
				time.Sleep(left)
			}
			continue
		}

		retryTimes = self.MaxRetry
		// 连接成功
		if self.OnDialCallback != nil {
			ok, readSize, ext := self.OnDialCallback(self, conn)
			if !ok {
				conn.Close()
				break
			}
			connx := &TCPConnEx{*conn, readSize, ext}
			if readSize > 0 {
				// readSize > 0 的时候走正常处理函数
				self.connReadHandler(connx)
			}
		} else {
			connx := &TCPConnEx{*conn, self.ReadBufSize, nil}
			self.connReadHandler(connx)
		}
	}
	return nil
}
