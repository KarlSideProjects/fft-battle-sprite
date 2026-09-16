# fft-battle-sprite

把 AI 生成的大尺寸角色動作圖，整理成輪廓清楚、比例與配色一致的低解析度戰鬥精靈圖。適合需要小型遊戲角色素材的開發者：這裡提供生成提示工作流、Python 後處理工具，以及可直接重做的 **64×64 透明 PNG 範例**。

![範例：同一位劍士的待機與攻擊共八幀](docs/example-frames.png)

先看[縮圖方法的差異](#為什麼不直接縮小圖片)，或從[隨附母圖重做八幀](#先重做隨附範例)開始；後者不需生成模型或外部帳號。

## 為什麼不直接縮小圖片？

生成圖看似像素畫，縮小後卻可能失去臉部、輪廓與色塊；不同動作分開處理，也容易讓角色攻擊時忽然變小或換色。這個專案把提示、人工檢查、共用縮放與調色盤串成可重做的素材流程。

![同一來源與目標尺寸：一般縮圖與眾數取樣的比較](docs/example-downscale.png)

核心做法是取每個來源區塊最常出現的顏色（眾數），再去除孤立雜點、重建暗色輪廓；不以平均混色決定所有輸出像素。這是隨附案例的比較，不代表所有縮圖演算法或所有素材的品質排名。

## 已有什麼？

- **可重做的素材**：[兩張透明母圖](examples/masters/)與[八張輸出](examples/frames/)，包含四幀待機、四幀攻擊；目前隨附範例沒有行走幀。
- **跨動作一致性**：同一次處理共用縮放比例及調色盤，以腳底區域定位，減少伸手或揮劍造成的左右漂移。
- **明確拒絕裁切**：姿勢超出目標格時以錯誤退出，提醒回頭修改動作輪廓。
- **可安裝的 agent skill**：[SKILL.md](SKILL.md) 包含待機、行走、攻擊的生成順序、提示模板與人工驗收步驟；[失敗案例](references/failure-modes.md) 說明陰影染色、頭身漂移與母圖被覆寫等問題。

它是素材製作工具，不含遊戲引擎、角色動畫播放器或自動品質評分器。新圖生成與去背仍需外部影像工具及人工檢查。

## 先重做隨附範例

需要 Python 3.10+。在 repo 根目錄執行：

```sh
git clone https://github.com/KarlSideProjects/fft-battle-sprite.git
cd fft-battle-sprite
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/pixelize_sprite.py \
  --sheet examples/masters/idle-2x2.png:2:2:idle_0,idle_1,idle_2,idle_3 \
  --sheet examples/masters/attack-2x2.png:2:2:attack_0,attack_1,attack_2,attack_3 \
  --cell 64 --colors 32 --out /tmp/fft-sprite-out
```

預期得到八張 64×64 RGBA PNG，終端逐幀列出尺寸與顏色數。可比較隨附輸出：

```sh
diff -r examples/frames /tmp/fft-sprite-out
```

無差異時 `diff` 不輸出訊息。2026-09-16 文件查核以 Python 3.12、Pillow 11.3.0、NumPy 2.2.6 重做此指令並比對；依賴檔只有最低版本，跨版本的 PNG 位元組一致性仍應實際檢查。

## 用於自己的角色

![由參考圖、生成母圖到像素幀的流程](docs/pipeline.svg)

先讀參考角色，產生並檢查待機圖；再以核准圖作為其他動作的參考。提示需明確約束頭部比例、目標像素預算、朝右攻擊、緊湊輪廓與中性陰影。完整提示在 [SKILL.md](SKILL.md)。

去背後保留透明母圖快照，再把**所有動作放進同一個指令**：

```sh
python scripts/pixelize_sprite.py \
  --sheet idle-clean.png:2:2:idle_0,idle_1,idle_2,idle_3 \
  --sheet walk-clean.png:2:2:walk_0,walk_1,walk_2,walk_3 \
  --sheet attack-clean.png:2:2:attack_0,attack_1,attack_2,attack_3 \
  --cell 64 --colors 32 --out out/
```

這三個輸入檔需自行準備；格式為 `PATH:ROWS:COLS:NAME[,NAME...]`，依由左到右、由上到下命名。輸入必須已透明，腳本不會替你移除洋紅背景。每格請給一個名稱；目前實作會輸出 `_a` 這類名稱，也將它們納入共同縮放／配色，不能把底線名稱當作跳過格子的功能。

| 選項 | 預設與取捨 |
| --- | --- |
| `--cell` | 必填；決定輸出方格尺寸 |
| `--colors` | 32；所有幀共用的最終調色盤上限 |
| `--mode-colors` | 256；取眾數前的色彩分桶，降低可壓掉雜色，也可能提前吃掉小面積高彩度細節 |
| `--feet-margin` | 3；腳底離輸出底邊的像素距離 |
| `--body-frac` | 0.70；以最高包圍盒決定全組縮放，不能修正原圖頭身比例漂移 |

長武器會擠壓角色本體的像素預算。超框時應重新生成更緊湊的姿勢，或把大型武器特效分層；單純調低 `--body-frac` 會縮小所有動作。產出後以整數倍放大檢查臉部、腳底線、出招方向與透明邊緣，仍須放進目標遊戲驗收。

## 安裝成 agent skill

安裝器需要 Node.js 18+ 與 npm。在要使用 skill 的專案根目錄執行：

```sh
npx github:KarlSideProjects/fft-battle-sprite
```

預設複製到 `.claude/skills/fft-battle-sprite` 及 `.codex/skills/fft-battle-sprite`。可加 `--claude` 或 `--codex` 只安裝一方，`--dir <path>` 指定專案；`--link` 改為存一份在 `.agents/skills/` 再連結。已有目錄會拒絕覆寫，只有 `--force` 會取代既有安裝，包含其中的本地修改。

安裝 skill 不等於安裝 Python 依賴或影像生成能力。後處理依賴可由安裝位置的 `requirements.txt` 安裝；生成階段需要 agent 實際可呼叫的影像工具。沒有影像工具時，仍可處理已備妥的母圖。

若想由 Git 追蹤 skill 版本，也可用 submodule：

```sh
git submodule add https://github.com/KarlSideProjects/fft-battle-sprite .agents/skills/fft-battle-sprite
mkdir -p .claude/skills .codex/skills
ln -s ../../.agents/skills/fft-battle-sprite .claude/skills/fft-battle-sprite
ln -s ../../.agents/skills/fft-battle-sprite .codex/skills/fft-battle-sprite
```

之後 clone 要加 `--recursive`，或執行 `git submodule update --init`。此段為支援符號連結的 shell 操作，目的路徑需尚未存在。

## 可以用來探究什麼？

同一張母圖可以比較平均混色與眾數取樣、48／64 像素預算，或分開／共同調色盤對動畫的影響。先固定輸入，再記錄輪廓、臉部與顏色的觀察，能把「看起來模糊」轉成可重做的影像處理問題；這是可延伸的探究活動，尚無課堂成效研究。

程式入口是 [pixelize_sprite.py](scripts/pixelize_sprite.py)，安裝流程是 [install.mjs](bin/install.mjs)。本輪驗證的是隨附素材重製及暫存專案的安裝／拒絕覆寫行為，未重新呼叫生成模型，也未驗收遊戲內動畫。

## 來源與授權

軟體及文件依 [MIT LICENSE](LICENSE)，保留 Karl（卡爾・詹）的著作權聲明。既有版本紀錄及套件 metadata 使用 `jhihweijhan/fft-battle-sprite` 路徑；本文件操作入口使用目前組織位置。

範例為 repo 既有工作流產生、處理的泛用劍士；「Final Fantasy Tactics style」是既有風格描述，不表示本專案擁有 Square Enix 的遊戲素材或取得其背書。生成所用模型／服務及輸入參考圖的權利需另行確認，MIT 軟體授權不能代替這些來源條件。
