import Std

/-!
Line-level model of _adaptive_fence, _advance_fence, and extract_code_blocks.
The opening line has already selected the generated fence. At width >= 3,
for a backtick or tilde marker, closing is exactly a matching fence prefix.
Body lines contain no embedded line separator. Python line splitting and
info-string parsing are separate boundary assumptions, checked by tests.
-/

namespace MarkdownFence

abbrev Line := List Char

def prefixRun (marker : Char) : Line → Nat
  | [] => 0
  | char :: rest => if char = marker then 1 + prefixRun marker rest else 0

def longestRun (marker : Char) : Line → Nat
  | [] => 0
  | char :: rest => max (prefixRun marker (char :: rest)) (longestRun marker rest)

def bodyBound (marker : Char) : List Line → Nat
  | [] => 0
  | line :: rest => max (longestRun marker line) (bodyBound marker rest)

def width (marker : Char) (body : List Line) : Nat :=
  max 3 (bodyBound marker body + 1)

def fence (marker : Char) (body : List Line) : Line :=
  List.replicate (width marker body) marker

theorem prefix_run_replicate_append (marker : Char) (count : Nat) (tail : Line) :
    prefixRun marker (List.replicate count marker ++ tail) = count + prefixRun marker tail := by
  induction count with
  | zero => simp
  | succ count ih => simp [List.replicate_succ, prefixRun, ih] <;> omega

/-- The reader's prefix test is equivalent to a sufficiently long leading run. -/
theorem fence_prefix_iff (marker : Char) (count : Nat) (line : Line) :
    (List.replicate count marker).IsPrefix line ↔ count ≤ prefixRun marker line := by
  constructor
  · rintro ⟨tail, rfl⟩
    rw [prefix_run_replicate_append]
    exact Nat.le_add_right count _
  · intro bound
    induction count generalizing line with
    | zero => exact ⟨line, rfl⟩
    | succ count ih =>
      cases line with
      | nil => simp [prefixRun] at bound
      | cons char rest =>
        by_cases same : char = marker
        · subst char
          have remaining : count ≤ prefixRun marker rest := by
            simp [prefixRun] at bound
            omega
          obtain ⟨tail, matched⟩ := ih rest remaining
          exact ⟨tail, by simp [List.replicate_succ, matched]⟩
        · simp [prefixRun, same] at bound

theorem prefix_run_le_longest (marker : Char) (line : Line) :
    prefixRun marker line ≤ longestRun marker line := by
  cases line with
  | nil => exact Nat.le_refl 0
  | cons char rest => exact Nat.le_max_left _ _

theorem line_run_le_body_bound (marker : Char) (body : List Line)
    (line : Line) (member : line ∈ body) : prefixRun marker line ≤ bodyBound marker body := by
  induction body with
  | nil => simp at member
  | cons first rest ih =>
    rcases List.mem_cons.mp member with same | later
    · subst line
      exact Nat.le_trans (prefix_run_le_longest marker first) (Nat.le_max_left _ _)
    · exact Nat.le_trans (ih later) (Nat.le_max_right _ _)

/-- No content line can be mistaken for the generated closing delimiter. -/
theorem adaptive_fence_separates_body (marker : Char) (body : List Line) :
    3 ≤ width marker body ∧ ∀ line ∈ body, ¬ (fence marker body).IsPrefix line := by
  constructor
  · exact Nat.le_max_left _ _
  · intro line member closes
    have runBound := line_run_le_body_bound marker body line member
    have opening := (fence_prefix_iff marker (width marker body) line).mp closes
    have grows : bodyBound marker body + 1 ≤ width marker body := Nat.le_max_right _ _
    omega

/-- Read after an opening fence, returning the body and the unconsumed suffix. -/
def readBody (marker : Char) (count : Nat) : List Line → List Line × List Line
  | [] => ([], [])
  | line :: rest =>
    if count ≤ prefixRun marker line then ([], rest)
    else
      let result := readBody marker count rest
      (line :: result.1, result.2)

theorem read_body_append_close (marker : Char) (count : Nat) (body suffix : List Line)
    (safe : ∀ line ∈ body, prefixRun marker line < count) :
    readBody marker count (body ++ List.replicate count marker :: suffix) = (body, suffix) := by
  have closing : prefixRun marker (List.replicate count marker) = count := by
    simpa [prefixRun] using prefix_run_replicate_append marker count []
  induction body with
  | nil => simp [readBody, closing]
  | cons first rest ih =>
    have firstSafe := safe first (List.mem_cons_self)
    have restSafe : ∀ line ∈ rest, prefixRun marker line < count := by
      intro line member
      exact safe line (List.mem_cons_of_mem first member)
    simp [readBody, Nat.not_le_of_gt firstSafe, ih restSafe]

/-- Wrapping preserves every body line and consumes exactly the generated close. -/
theorem adaptive_roundtrip (marker : Char) (body suffix : List Line) :
    readBody marker (width marker body) (body ++ fence marker body :: suffix) = (body, suffix) := by
  apply read_body_append_close
  intro line member
  have separate := (adaptive_fence_separates_body marker body).2 line member
  have notPrefix : ¬ (List.replicate (width marker body) marker).IsPrefix line := separate
  have notEnough : ¬ width marker body ≤ prefixRun marker line := by
    intro enough
    exact notPrefix ((fence_prefix_iff marker (width marker body) line).mpr enough)
  omega

end MarkdownFence
