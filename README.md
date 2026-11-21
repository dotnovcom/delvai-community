# 得律AI 社区版

电脑端法律咨询、会话、公告，以及这些功能对应的管理后台和后端。

手机端、合同、检索、文书、律师、语音视频、企业、会员和支付不在本仓库。这些能力留在商业版，商业版不公开。

## 许可

代码以 GNU Affero General Public License v3.0 授权，见 [LICENSE](LICENSE)。

「得律AI」名称和 Logo 不随这份代码许可授权，见 [TRADEMARK.md](TRADEMARK.md)。

## 本地运行

需要 Docker。

```bash
cp .env.example .env
docker compose up --build
```

- 用户端：http://localhost:8080
- 管理端：http://localhost:8081 ，首次管理员见 `.env` 里的 `ADMIN_BOOTSTRAP_*`
- 接口：http://localhost:8000

首次启动会执行 `alembic upgrade head`，只创建社区版用到的表。

在管理端「对话模型」填入你自己的对话模型地址和密钥。咨询额度按本地每日次数计算，默认每天 5 次，可在 `.env` 修改 `FREE_DAILY_CHAT_QUOTA`。
