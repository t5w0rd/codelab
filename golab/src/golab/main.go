package main

import (
	"fmt"
	"log"
	"net"
	"os"
	"tutils"
)

func printb(data []byte) {
	for _, x := range data {
		fmt.Printf("%02x ", x)
	}
	println()
}

func sendchan(c chan int) {
	for i := 0; ; i++ {
		c <- i
	}
}

func onHandle(self *tutils.TcpServer, conn *tutils.TCPConnEx, connId uint32, data []byte) (ok bool) {
	println(string(data))
	return true
}

func onDial(self *tutils.TcpClient, conn *net.TCPConn) (ok bool, readSize int, connExt interface{}) {
	println("conn succ")
	return true, self.ReadBufSize, nil
}

func test() {

}

func main() {
	log.SetFlags(log.Lshortfile | log.LstdFlags)
	args := os.Args
	if len(args) < 2 {
		return
	}
	appType := args[1]
	switch appType {
	case "proxy":
		peerAddrStr := args[2]
		peerAddr, err := net.ResolveTCPAddr("tcp", peerAddrStr)
		if err != nil {
			println(err.Error())
			return
		}

		peer, err := net.DialTCP("tcp", nil, peerAddr)
		if err != nil {
			println(err.Error())
			return
		}
		defer peer.Close()

		addrStr := args[3]
		tutils.NewEncryptTunProxy(peer, addrStr).Start()

	case "agent":
		peerAddrStr := args[2]
		peerAddr, err := net.ResolveTCPAddr("tcp", peerAddrStr)
		if err != nil {
			println(err.Error())
			return
		}

		println("listen on: " + peerAddrStr)
		lstn, err := net.ListenTCP("tcp", peerAddr)
		if err != nil {
			println(err.Error())
			return
		}

		peer, err := lstn.AcceptTCP()
		if err != nil {
			println(err.Error())
			return
		}
		defer peer.Close()
		println("accept")

		addrStr := args[3]
		tutils.NewEncryptTunAgent(peer, addrStr).Start()

	case "messager":
		addr := args[2]
		tutils.StartMessagerServer(addr)

	case "test":
		test()

	case "proxyx":
		clt := tutils.NewTcpClient()
		clt.Addr = os.Args[2]
		clt.OnDialCallback = func(self *tutils.TcpClient, conn *net.TCPConn) (ok bool, readSize int, connExt interface{}) {
			proxy := tutils.NewEncryptTunProxy(conn, os.Args[3])
			proxy.Start()
			return false, 0, proxy
		}

	case "agentx":
		svr := tutils.NewTcpServer()
		svr.Addr = os.Args[2]
		svr.OnAcceptConnCallback = func(self *tutils.TcpServer, conn *net.TCPConn, connId uint32) (ok bool, readSize int, connExt interface{}) {
			agent := tutils.NewEncryptTunAgent(conn, os.Args[3])
			go agent.Start()
			return true, 0, agent
		}
	}
}
