# Task: Bug Diagnosis & Root Cause Analysis
# Input: $ARGUMENTS

步驟：
1. 重現分析：分析錯誤訊息或異常行為描述。
2. 代碼搜尋：使用 grep 或 ls 定位可能的出錯點。
   若需大範圍搜尋 (超過 3 個檔案)，使用 sub-agent 執行，僅回傳摘要至主 session。
3. 原因解釋：說明為何會發生此問題 (Root Cause)。
4. 修復建議：提出修復方案，並檢查是否會對其他模組造成 Side Effect。
