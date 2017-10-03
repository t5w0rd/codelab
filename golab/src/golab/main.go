package main

import (
    "tutils"
    "os"
    "net"
    "log"
    "fmt"
)

func printb(data []byte) {
    for _, x := range data {
        fmt.Printf("%02x ", x)
    }
    println()
}

func sendchan(c chan int) {
    for i:= 0; ; i++{
        c <- i
    }
}

func test() {
    c := make(chan int, 5)
    //go sendchan(c)
    //time.Sleep(1e9)
    c <- 5
    c <- 4
    select {
    case <-c:
        a := <-c
        println(a)
    default:
        println("def")

    }
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
    }
}
