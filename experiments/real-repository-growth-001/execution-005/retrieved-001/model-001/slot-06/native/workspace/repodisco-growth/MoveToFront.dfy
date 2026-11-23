// RepoDisco extension to pinned Dafny-VMC; this file is analyst-authored.
module RepoDiscoGrowthShift {
  import Model = FisherYates.Model
  export Public provides MoveToFront

  function MoveToFront<T>(xs: seq<T>, k: nat): (ys: seq<T>)
    requires k < |xs|
    ensures ys == [xs[k]] + xs[..k] + xs[k+1..]
    ensures |ys| == |xs|
    ensures multiset(ys) == multiset(xs)
    decreases k
  {
    // BEGIN MODEL BODY
if k == 0 then
      xs
    else
      var prev := MoveToFront(xs, k - 1);
      var swapped := Model.Swap(prev, 0, k);
      swapped
    // END MODEL BODY
  }
}
