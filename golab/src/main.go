package main

import (
	"tutils"
	"os"
	"net"
)


func main() {
	args := os.Args;
	appType := args[1];
	switch appType {
	case "proxy":
		peerAddrStr := args[2];
		peerAddr, err := net.ResolveTCPAddr("tcp", peerAddrStr);
		if err != nil {
			println(err.Error());
			return;
		}

		peer, err := net.DialTCP("tcp", nil, peerAddr);
		if err != nil {
			println(err.Error());
			return;
		}
		defer peer.Close();

		proxyAddrStr := args[3];
		tutils.EncryptProxy(peer, proxyAddrStr);
	case "agent":
		peerAddrStr := args[2];
		peerAddr, err := net.ResolveTCPAddr("tcp", peerAddrStr);
		if err != nil {
			println(err.Error());
			return;
		}

		lstn, err := net.ListenTCP("tcp", peerAddr);
		if err != nil {
			println(err.Error());
			return;
		}

		peer, err := lstn.AcceptTCP();
		if err != nil {
			println(err.Error());
			return;
		}
		defer peer.Close();

		agentAddrStr := args[3];
		tutils.EncryptAgent(peer, agentAddrStr);
	}
}