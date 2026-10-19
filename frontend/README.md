# 前端

Vue 3 + TypeScript + Axios + Vue Router。

```bash
npm install
npm run dev      # http://127.0.0.1:5173 ，/api 代理到 Flask :8765
npm run build    # 构建到 dist，供 Flask 托管
npm test
```

接口封装在 `src/api/`，积分榜计算在 `src/lib/standings.ts`。
