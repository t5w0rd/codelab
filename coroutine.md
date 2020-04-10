# 高效的I/O编程体系的核心技术原理
> 开发高效
> 运行高效

## 技术应用
* Python gevent/asyncio
* OpenResty cosocket
* Golang netpool

## 章节目录
1. 协程
2. 事件模型
3. 高效IO编程体系


## 基于 协程 和 IO事件模型 建立 高效IO编程体系


## 第一章 协程

> 学习方法：我们结合我们熟悉的线程这个模型来进行对比分析。

1. 协程与线程类似，也是以一个函数作为执行主体的。与线程一样，协程的创建返回的是一个协程对象；这个协程对象可以想象成一个实例化的虚拟机

2. 线程是委托给操作系统去调度；协程是由开发者去调度；所以协程创建之后他不会主动运行；

3. 如果想要通过逻辑去暂停一个线程的运行，通常需要靠条件变量(cond、python下是Event)或互斥锁(mutex)来控制，即线程不想听你说话，只能给他挖坑，让他陷入泥潭无法执行。相比之下协程就显得很听话，说停就停，说跑就跑

4. 协程模型最重要的两个控制语义yield和resume；
浅层面的理解：yield是放弃执行使协程暂停，在协程主体函数内部调用；resume是恢复暂停中的协程使其继续执行，在普通lua逻辑中调用；而更深层面的理解是：协程的主体逻辑的运行环境跟外部普通逻辑的运行环境相当于是不同的两个世界。两个世界不会同时运转，但会通过yield和resume交替运转。yield将使世界的执行权从协程转向外层世界，resume使执行权从普通世界转向协程世界；

5. resume和yield的“带货”(数据交换)，通常它们在交换执行权的时候还会给对方带点“货”，即resume的参数会通过yield返回，yield的参数会通过resume返回

6. 什么时候应该去yield呢，用一个常见的情景

```lua
func = function(a, b, c)
    x, y, z = coroutine.yield(a + b, b + c, c + a)
    return x, y, z
end

local co = coroutine.create(func)

print("resume", coroutine.resume(co, 1, 2, 3))
print("resume", coroutine.resume(co, 1, 2, 3))

coroutine vm|real lua
yield     <-|->  resume

-- 打印 resume true 3 5 4 yield时，返回yield的参数
-- 打印 resume true 1 2 3 resume时，返回resume的参数
```


## 第二章 事件模型

### 事件模型的开发
* Windows开发游戏引擎
* 多路复用
* 量化策略事件引擎


#### 多路复用模型,select,pool,kqueue,epoll,complete port

#### 首先，事件模型的原型

```python
def event_loop:
    event = event_wait(reg_event_list)
    handle(event)

def handle(event):
    ...
    reg_event(event)

```

#### 事件模型的小改进(事件引擎原理)
```
def create_event_engine():
    pass

def event_wait(engine):
    pass

def reg_event(engine, event_key, hansdler):
    event.key = event_key
    event.handler = handler

def event_loop(engine):
    while True:
        event = event_wait(engine)
        event_dispatch(event)

def event_dispatch(engine, event):
    handler = engine.handlers[event.key]
    handler(event)
```


#### epoll就是只关注IO事件的事件模型
#### 有了IO事件模型之后，接下来就可以构建一个异步io编程体系了


#### python async IO async await

#### python 基于协程的异步编程

#### 案例1 asyncio
```python
async def get_msg(url):
    await rsp = sock.recv(url)
    await db.write(rsp)


aysnc def main():
    co1 = get_msg(url1)
    co2 = get_msg(url2)
    await asyncio.gather(co1, co2)


co = main()
asyncio.run(main())

```

#### 案例2 python gevent
```python
from gevent import monkey
monkey.patch_all()
```


## 第三章 高效IO编程体系
> 以cosocket的实现原理为例进行说明

### cosocket的原理，python表达
```python
class CoSocket:
  def __init__(self):
      self.sock = socket.socket()
  
  def recv(self):
      reg_event(global.engine, EVENT_READ, self.on_recv_event)
      data = yield
      return data

  def on_recv_event(self, event):
      data = self.sock.recv()
      resume(data)


# 用户的业务逻辑处理函数(协程函数)
def user_request_handler():
    sock = CoSocket()
    data = sock.recv()


# 服务内部实现
# 服务事件循环
def event_loop(engine):
    while True:
        event = event_wait(engine)
        event.handler(event)

# 每次服务请求到达
def service_request_handler():
    resume(user_request_handler)

# 服务启动
engine = create_event_engine()
event_loop(engine)

```

## 协程的其他魔幻用法
### 曾经制作的一款游戏，计算插播渲染
```python
def render_loop():
    render()  # 载荷函数
    sleep(t)  # 控制帧率
```