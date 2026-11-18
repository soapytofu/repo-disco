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
    assert xs == xs[..k] + [xs[k]] + xs[k+1..];
    var ys := [xs[k]] + xs[..k] + xs[k+1..];
    calc {
      multiset(ys);
      multiset([xs[k]]) + multiset(xs[..k]) + multiset(xs[k+1..]);
      multiset(xs[..k]) + multiset([xs[k]]) + multiset(xs[k+1..]);
      multiset(xs);
    }
    ys
    // END MODEL BODY
  }
}
