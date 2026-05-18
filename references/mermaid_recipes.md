# Mermaid 图表写法参考

供 aggregator.py 生成 Mermaid 代码时参考，也可用于手动编辑 HTML 中的图表。

## 1. 时序图 (Sequence Diagram)

最常用——描述一个 API 请求从客户端到数据库的完整调用链路。

```mermaid
sequenceDiagram
    participant Client as 客户端/前端
    participant Ctrl as OrderController
    participant Svc as OrderService
    participant InvSvc as InventoryService
    participant Mapper as OrderMapper
    participant DB as 数据库

    Client->>Ctrl: POST /api/orders (OrderDTO)
    Ctrl->>Svc: createOrder(dto)
    Svc->>InvSvc: deductStock(skuId, qty)
    InvSvc-->>Svc: 库存充足
    Svc->>Mapper: insert(order)
    Mapper->>DB: INSERT INTO orders
    DB-->>Mapper: orderId=12345
    Mapper-->>Svc: orderId
    Svc-->>Ctrl: Result(orderId)
    Ctrl-->>Client: 200 OK
```

**箭头含义：**
- `->>` 实线箭头（同步调用）
- `-->>` 虚线箭头（返回/响应）
- `->>+` 激活目标
- `-->>-` 返回并停用

## 2. 流程图 (Flowchart)

描述包含条件分支的业务决策流程。

```mermaid
flowchart TD
    A[接收下单请求] --> B{参数校验}
    B -->|校验失败| C[返回 400 参数错误]
    B -->|校验通过| D{库存是否充足}
    D -->|充足| E[锁定库存]
    D -->|不足| F[返回库存不足]
    E --> G[创建订单]
    G --> H{有无优惠券}
    H -->|有| I[计算优惠金额]
    H -->|无| J[按原价计算]
    I --> K[保存订单]
    J --> K
    K --> L[发送MQ通知]
    L --> M[返回订单ID]
```

**节点形状：**
- `[ ]` — 矩形（普通步骤）
- `{ }` — 菱形（条件判断）
- `(( ))` — 圆形
- `[( )]` — 圆角矩形（数据库）

## 3. 实体关系图 (ER Diagram)

描述数据模型之间的关系。

```mermaid
erDiagram
    Order ||--o{ OrderItem : "包含"
    Order ||--|| Payment : "关联"
    OrderItem }o--|| Product : "引用"
    Order }o--|| User : "属于"
    
    Order {
        Long id PK
        Long userId FK
        BigDecimal totalAmount
        String status
        DateTime createTime
    }
    
    OrderItem {
        Long id PK
        Long orderId FK
        Long skuId FK
        Integer quantity
        BigDecimal price
    }
```

## 4. 常用电商模式速查

### 下单流程时序图

```
sequenceDiagram
    Client->>OrderController: POST /order/create
    OrderController->>OrderService: createOrder(dto)
    OrderService->>InventoryService: checkStock(items)
    InventoryService-->>OrderService: stock OK
    OrderService->>InventoryService: lockStock(items)
    OrderService->>CouponService: validateCoupon(code)
    CouponService-->>OrderService: discount
    OrderService->>OrderMapper: insert(order)
    OrderService->>MQService: sendMessage("order.created")
    OrderService-->>OrderController: orderId
    OrderController-->>Client: 200 {orderId}
```

### 退款流程时序图

```
sequenceDiagram
    Client->>RefundController: POST /refund/apply
    RefundController->>RefundService: applyRefund(orderId, reason)
    RefundService->>OrderService: getOrder(orderId)
    OrderService-->>RefundService: order
    RefundService->>PaymentService: refund(order.paymentId, amount)
    PaymentService-->>RefundService: refundId
    RefundService->>InventoryService: restoreStock(items)
    RefundService->>OrderService: updateStatus(orderId, REFUNDING)
    RefundService-->>RefundController: refundId
    RefundController-->>Client: 200 {refundId}
```

### 秒杀流程流程图

```
flowchart TD
    A[接收秒杀请求] --> B{活动进行中?}
    B -->|否| C[返回活动未开始/已结束]
    B -->|是| D{用户已参与过?}
    D -->|是| E[返回不能重复参与]
    D -->|否| F{库存 > 0?}
    F -->|否| G[返回已抢光]
    F -->|是| H[扣减库存]
    H --> I{扣减成功?}
    I -->|失败| G
    I -->|成功| J[创建订单]
    J --> K[发送抢购成功通知]
    K --> L[返回下单成功]
```

## 常见问题

### Mermaid 图太大/太小
在 HTML 的 `<pre class="mermaid">` 外层的 `.mermaid-block` 可以用 CSS 调整尺寸。

### 中文显示问题
Mermaid 支持中文，但部分特殊字符需要引号包裹。aggregator.py 已经自动处理。

### CDN 加载失败
现象：图表区域显示「Mermaid.js 未加载」。
解决：下载 `mermaid.min.js` 放到 HTML 同目录，刷新页面。
