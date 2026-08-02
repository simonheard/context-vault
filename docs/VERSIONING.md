# 版本与兼容同步

[English](VERSIONING.en.md)

ContextVault 分开管理四种版本：Python 产品版本、SQLite schema、客户端协议和具体适配器版本。
当前为产品 `0.11.0`、schema `9`、协议 `3`、Chrome 扩展 `0.4.0`，最低兼容客户端协议为 `2`。独立扩展资料库 schema 为 `1`。

- `/api/version` 在读取 route 前完成握手；
- 扩展发送 `X-ContextVault-Protocol`，超出服务端 min/max 时返回 HTTP 426；
- `sync_clients` 记录扩展或未来设备客户端的产品版本、协议、状态和最后在线时间；
- `sync_events.protocol_version` 允许新客户端识别旧事件格式；
- `schema_migrations` 与幂等列迁移允许旧 vault 原地升级；
- CLI managed block 匹配所有旧 protocol 标记并原位替换；
- profile 和 receipt 使用内容 hash 版本，diff 只基于最后 completed receipt；
- 协议 2 客户端仍在当前兼容窗口内工作；协议低于 minimum 时要求升级客户端，高于 server 时要求升级服务端。

数据库升级前应备份 `vault.sqlite`。协议提升时应先发布能够同时读取旧/新格式的服务端，再更新扩展，
最后在下一个大版本提高 minimum protocol，避免服务端与浏览器同时强制升级造成停机。
