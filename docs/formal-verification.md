# 適応フェンスの本文保持の形式検証

`formal/FenceRoundtrip.lean` は、`_adaptive_fence()`、`_advance_fence()`、
`extract_code_blocks()` の関係を行単位のモデルで検証します。
生成したフェンスが本文中の行で早く閉じないことに加え、読み取りが **本文の全行をそのまま返し、
生成した閉じフェンスの後ろを消費せずに残す**ことを証明します。

共通ラッパー `lean_verify.py` と Lean 専用 CI は
[親リポジトリ](https://github.com/myon-bioinformatics/myon-bioinformatics/blob/6c2558c4251698c50bc07bad86fb49f902b2738f/lean_verify.py)
で管理します。このリポジトリは固有の証明と接続テストを持ち、通常実行の依存は増やしません。

## 証明する処理

本文を文字の列からなる行のリストとして扱います。`prefixRun` は行頭の同じ文字の連続数、
`longestRun` は行中の最大連続数、`bodyBound` は本文全体の上限です。
生成する長さは実装と同じ `max(3, bodyBound + 1)` です。

ここでは数値の大小だけで終えず、同じ文字を繰り返したフェンスが行の接頭部になる条件を証明します。
続いて本文のどの行にもその接頭部がないことを示し、閉じ行を読むまで本文を収集する再帰処理に接続します。

| 定理 | 内容 | 実装との対応 |
| --- | --- | --- |
| `MarkdownFence.prefix_run_replicate_append` | 繰り返したフェンス文字と後続文字列の先頭連続数 | 生成した文字列の構造 |
| `MarkdownFence.fence_prefix_iff` | フェンスが接頭部であることと、先頭連続数が十分であることの同値 | `line.startswith(active_fence)` |
| `MarkdownFence.prefix_run_le_longest` | 行頭の連続数は行内の最大連続数以下 | `_adaptive_fence` の上限 |
| `MarkdownFence.line_run_le_body_bound` | 各本文行の先頭連続数は本文全体の上限以下 | 行への分割と上限の関係 |
| `MarkdownFence.adaptive_fence_separates_body` | フェンス長が 3 以上で、どの本文行も閉じフェンスにならない | `_advance_fence` の本文中の状態保持 |
| `MarkdownFence.read_body_append_close` | 早く閉じない本文を読むと、本文と閉じ行の後の残りを正確に分離する | `extract_code_blocks` の本文収集 |
| `MarkdownFence.adaptive_roundtrip` | 適応フェンスで囲った本文の全行を保持し、生成した閉じ行だけを消費する | 生成と読み取りの接続 |

長さは特定の値に制限していません。本文中に 3 個や 4 個のフェンス文字がある場合だけでなく、
任意の長さ・行数について成立します。

## 入力と境界の前提

実際の Python との対応では次の条件を置きます。

- フェンス文字は API が受け付けるバッククォートまたはチルダ。
- 開き行は生成したフェンス長のまま認識される。`lang` は空、または有効な単一行の info string。
  開きフェンスと同じ文字を直接先頭に続けて、開き側だけ長くする入力は対象外。
- 本文は LF で区切った行として扱う。各行の中には `splitlines()` が別の改行と認識する文字を含めない。

この条件では、末尾の LF や空行を含む本文も保持します。
一方、`extract_code_blocks()` は `splitlines()` と LF での結合を使うため、CRLF、CR、
Unicode の行区切りなどを LF に正規化します。任意の入力のバイト列を復元するという主張はしません。
info string は `strip()` され、先頭トークンが `language` になるため、その空白も本文とは別に扱います。

モデルは開き行の認識後から始まります。正規表現、info string の解析、文字列の行分割、
Python の全実行は形式証明の対象外です。

## Python との接続テスト

既存の `tests/test_syntax.py` にある個々のフェンスの例はそのまま使います。
新しい `tests/test_formal_bridge.py` では、例を重ねる代わりに次を確認します。

- バッククォート・チルダ・通常文字・LF の 4 文字で作る長さ 0〜6 の **5,461 本文**を、
  両フェンス文字で検査する **10,922 組**。独立した逐次カウンタで長さを比較し、実際の
  スキャナが本文行を開閉行と取り違えず、抽出した本文が一致することを確認。
- **12 段の入れ子**を各段で読み戻し、後続の見出しと別のコードブロックが本文に飲み込まれないことを確認。
- 日本語、結合文字、絵文字、タブ、末尾空行、通常のメタデータを含む本文を確認。
- CR・CRLF・Unicode 行区切りなどの正規化を明示的に確認し、完全なバイト保持と混同しない。

テストは 4 件で、標準ライブラリだけで動きます。これらの有限検査から、Python の全入力への証明は主張しません。

```sh
python -S -m unittest discover -s tests -p test_formal_bridge.py -v
```

この接続テストは通常の pytest でも収集されます。既存の pytest 所有のテスト全体を
`unittest` で読み込む必要はありません。

## Lean 専用の検証

`formal/lean-toolchain` は `leanprover/lean4:v4.36.0` です。Lean 同梱の `Std` を使い、Mathlib は不要です。
親リポジトリを隣の `myon-bioinformatics` に置いた場合、次のように実行できます。

```sh
python -S ../myon-bioinformatics/lean_verify.py \
  --cwd formal --required --json-output build/lean-verification.json \
  --theorem MarkdownFence.prefix_run_replicate_append \
  --theorem MarkdownFence.fence_prefix_iff \
  --theorem MarkdownFence.prefix_run_le_longest \
  --theorem MarkdownFence.line_run_le_body_bound \
  --theorem MarkdownFence.adaptive_fence_separates_body \
  --theorem MarkdownFence.read_body_append_close \
  --theorem MarkdownFence.adaptive_roundtrip \
  FenceRoundtrip.lean
```

共有ラッパーは Lean 未導入を `unverified` と記録します。`--required` を使う専用 CI は、
未検証と証明失敗を失敗として扱います。通常の Python テストから Lean は実行しません。
今回の定理は `propext`・`Quot.sound` の範囲で公理監査に通り、独自公理や未完了の証明はありません。

HTML 変換の安全性、任意の Markdown 処理系との一致、CommonMark 全体への適合、
自然言語の意味の保存は今回の対象ではありません。読み取り側には、フェンスの後に文字が続く行も
閉じ行にする既存の字句規則があり、この証明はその実装に対応するものです。
