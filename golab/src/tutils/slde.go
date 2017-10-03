package tutils

import (
    "encoding/binary"
    "bytes"
    "errors"
    "math/rand"
    "log"
    //"time"
)

const SLDE_STX byte = 2
const SLDE_ETX byte = 3
const SLDE_CUSTOM_SIZE int = 1  // TODO: add custom size
const SLDE_LENGTH_SIZE int = 4
const SLDE_HEADER_SIZE int = SLDE_CUSTOM_SIZE + SLDE_LENGTH_SIZE + 1

type Slde struct {
    writebuf *bytes.Buffer
    length int

    // custom fields
    rid uint32
}

func XorEncrypt(data []byte, seed int64) (ret []byte) {
    ret = make([]byte, len(data))
    rnd := rand.New(rand.NewSource(seed))
    for i, v := range data {
        ret[i] = v ^ byte(rnd.Intn(256))
    }
    return ret
}

func (self *Slde) Write(data []byte) (int, error) {
    self.writebuf.Write(data)

    if self.writebuf.Len() < SLDE_HEADER_SIZE {
        // header not enough
        return SLDE_HEADER_SIZE - self.writebuf.Len(), nil
    }

    if self.length < 0 {
        // header enough
        var stx byte
        binary.Read(self.writebuf, binary.BigEndian, &stx)
        if stx != SLDE_STX {
            return -1, errors.New("field stx err")
        }

        // TODO: add custom field
        var stx2 byte
        binary.Read(self.writebuf, binary.BigEndian, &stx2)
        //binary.Read(self.writebuf, binary.BigEndian, &self.rid)
        //log.Printf("decode slde.rid: %04X\n", self.rid)

        var length int32
        binary.Read(self.writebuf, binary.BigEndian, &length)
        if length < 0 {
            return -1, errors.New("field length err")
        }
        self.length = int(length)
        log.Println("decode slde.length:", self.length)
    }

    left := self.length + 1 - self.writebuf.Len()
    if left > 0 {
        return left, nil
    }

    // write finished
    etx := self.writebuf.Bytes()[self.length]
    if etx != SLDE_ETX {
        return -1, errors.New("field etx err")
    }

    return 0, nil
}

func (self *Slde) Decode() (ret []byte, err error) {
    if self.length < 0 || self.writebuf.Len() != self.length + 1 {
        println(self.length, self.writebuf.Len())
        return nil, errors.New("data format err")
    }

    ret = self.writebuf.Bytes()[:self.length]
    ret = XorEncrypt(ret, 776103)
    return ret, nil
}

func (self *Slde) Encode(data []byte) ([]byte, error) {
    data = XorEncrypt(data, 776103)
    self.length = len(data)
    log.Println("encode slde.length:", self.length)
    self.writebuf.Reset()
    binary.Write(self.writebuf, binary.BigEndian, SLDE_STX)

    // TODO: add custom fields
    //rnd := rand.New(rand.NewSource(time.Now().UnixNano()))
    //self.rid = rnd.Uint32()
    //log.Printf("encode slde.rid: %04X\n", self.rid)
    //binary.Write(self.writebuf, binary.BigEndian, self.rid)
    binary.Write(self.writebuf, binary.BigEndian, SLDE_STX)

    binary.Write(self.writebuf, binary.BigEndian, int32(self.length))
    self.writebuf.Write(data)
    binary.Write(self.writebuf, binary.BigEndian, SLDE_ETX)
    return self.writebuf.Bytes(), nil
}

func (self *Slde) Bytes() []byte {
    return self.writebuf.Bytes()
}

func (self *Slde) Reset() {
    self.writebuf.Reset()
    self.length = -1
}

func NewSlde() *Slde {
    obj := new(Slde)
    obj.writebuf = bytes.NewBuffer([]byte{})
    obj.length = -1
    return obj
}

func NewSldeWithData(data []byte) *Slde {
    obj := new(Slde)
    obj.writebuf = bytes.NewBuffer([]byte{})
    obj.Encode(data)
    return obj
}