# Task: Project Onboarding & Persistence

請分三階段執行，並將所有進度實體化記錄於檔案中：

### Phase 1: 掃描與同步
- 檢查是否存在 docs/CODEBASE.md。
- 若已存在：讀取並驗證與目前代碼是否一致，指出差異點。
- 若不存在：掃描目錄結構、package.json、CLAUDE.md，建立初版 docs/CODEBASE.md。
- 匯報：簡述目前對技術棧與架構的理解。

### Phase 2: 邏輯深挖
- 追蹤核心資料流 (Data Flow) 與關鍵進入點。
- 更新 docs/CODEBASE.md，加入模組權責與關鍵商務邏輯。
- 提問：條列不確定或代碼中模糊的地方。請等待回覆再繼續。

### Phase 3: 知識封存
- 根據回覆，產出 docs/ONBOARDING.md 作為新人指南。
- 確保以後即使執行 /clear，只要讀取 docs/CODEBASE.md 就能立刻接手任務。
