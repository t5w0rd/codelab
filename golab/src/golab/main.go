package main

import (
    "tutils"
    "os"
    "net"
    "time"
)

func test() {
    addr, _ := net.ResolveTCPAddr("tcp", "localhost:2888")
    conn, _ := net.DialTCP("tcp", nil, addr)
    go func() {
        buf := make([]byte, 4096)
        for {
            n, err := conn.Read(buf)
            if err != nil {
                println(err.Error())
                break
            }
            if n <= 0 {
                println("remote closed")
            }

            println(buf)
        }
        conn.Close()
    }()
    v := make(chan int)
    close(v)
    time.Sleep(5 * 1e9)
    conn.Close()
    time.Sleep(5 * 1e9)
}

func main() {
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
    }
}
