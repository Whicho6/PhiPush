# Security policy

## Reporting a vulnerability

Please report security issues privately to the repository maintainer instead
of opening a public issue. Do not include a SessionToken, TapTap access token,
cloud-save archive, cookie, authorization header, or another player's data in
any report.

## Credential handling

PhiPush is designed to keep real credentials in process memory only. A
SessionToken grants access to a player's cloud save and must be treated as a
password. Public deployments must use HTTPS, disable request-body logging,
restrict CORS, apply rate limits, and keep private deployment configuration out
of the repository.

The public repository contains no bundled TapTap/LeanCloud credentials or game decryption parameters. Configure them locally through environment variables. Never add a client secret, Master Key, private server secret, or decryption key to this repository.

## Public repository checks

GitHub Actions 只安装依赖并运行本地 pytest，不请求真实接口，不读取仓库 secrets，也不输出请求正文、SessionToken、cookie 或认证头。提交前应扫描完整 Git 历史；如果凭证曾被提交，必须轮换凭证并重写历史，删除当前文件并不足够。
