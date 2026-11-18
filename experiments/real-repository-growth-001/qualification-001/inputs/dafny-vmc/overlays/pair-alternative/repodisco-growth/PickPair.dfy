// RepoDisco extension to pinned Dafny-VMC; this file is analyst-authored.
module FisherYates.GrowthPick {
  import Shift = FisherYates.GrowthShift`Public
  export Public provides PickPair

  function PickPair<T>(xs: seq<T>, i: nat, j: nat): (ys: seq<T>)
    requires i < j < |xs|
    ensures ys == [xs[i], xs[j]] + xs[..i] + xs[i+1..j] + xs[j+1..]
    ensures |ys| == |xs|
    ensures multiset(ys) == multiset(xs)
    decreases 0
  {
    // BEGIN MODEL BODY
    var secondFirst := Shift.MoveToFront(xs, j);
    assert secondFirst == [xs[j]] + xs[..j] + xs[j+1..];
    assert xs[..j] == xs[..i] + [xs[i]] + xs[i+1..j];
    assert secondFirst[i+1] == xs[i];
    assert secondFirst[..i+1] == [xs[j]] + xs[..i];
    assert secondFirst[i+2..] == xs[i+1..j] + xs[j+1..];
    var ys := Shift.MoveToFront(secondFirst, i+1);
    assert ys == [xs[i], xs[j]] + xs[..i] + xs[i+1..j] + xs[j+1..];
    ys
    // END MODEL BODY
  }
}
