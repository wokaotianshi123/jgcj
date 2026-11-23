# jgcj

采集源来自两个站点的结果，合并去重后生成各平台配置：

- 源 A：影视站之家 <https://www.yszzq.com/tags/xmlcjjk/>（`xinpq.py` → `lins.py` → `maqu.txt`）
- 源 B：zzzypro <https://www.zzzypro.com/>（`extract_zzzy.py` → `maqu1.txt`）

两个采集任务在 `main.yml` 流水线里**并行运行**，随后由 `merge` 任务合并、按接口地址去重，
再统一生成 6 份配置。`main.yml` 与 `main2.yml` 都在同一时间定时触发（每 3 天），
`main2.yml` 调用同一条流水线；`concurrency` 保证两次运行排队，不会互相覆盖。

## 配置文件

```
https://a.wokaotianshi.eu.org/jgcj/zcying.json
```
资源影视（v影格式，合并后的全量源）

```
https://a.wokaotianshi.eu.org/jgcj/zyvying.json
```
v影（合并后的全量源）

```
https://a.wokaotianshi.eu.org/jgcj/zytvbox.json
```
TVBox

```
https://a.wokaotianshi.eu.org/jgcj/ysdqbox.json
```
影视大全（旧格式，保留兼容）

```
https://a.wokaotianshi.eu.org/jgcj/zypcbox.json
```
zypc 版

```
https://a.wokaotianshi.eu.org/jgcj/libretv.json
```
LibreTV

```
https://a.wokaotianshi.eu.org/jgcj/hongguo.json
```
红果

## 本地重新生成

```bash
python xinpq.py && python lins.py   # 生成 maqu.txt
python extract_zzzy.py maqu1.txt     # 生成 maqu1.txt
python build_json.py maqu.txt maqu1.txt
```
