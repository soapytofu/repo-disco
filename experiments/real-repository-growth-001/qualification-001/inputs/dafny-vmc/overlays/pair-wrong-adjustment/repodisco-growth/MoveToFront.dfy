// RepoDisco extension to pinned Dafny-VMC; this file is analyst-authored.
module FisherYates.GrowthShift {
  import Model
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
      assert xs == [xs[0]] + xs[1..];
      xs
    else
      var swapped := Model.Swap(xs, k-1, k);
      assert swapped == xs[..k-1] + [xs[k]] + [xs[k-1]] + xs[k+1..];
      assert swapped[k-1] == xs[k];
      assert swapped[..k-1] == xs[..k-1];
      assert swapped[k..] == [xs[k-1]] + xs[k+1..];
      assert xs[..k] == xs[..k-1] + [xs[k-1]];
      var ys := MoveToFront(swapped, k-1);
      assert ys == [xs[k]] + xs[..k] + xs[k+1..];
      ys
    // END MODEL BODY
  }
}
