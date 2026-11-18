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
    var first := Shift.MoveToFront(xs, i);
    var tail := first[1..];
    assert first == [xs[i]] + xs[..i] + xs[i+1..];
    assert tail == xs[..i] + xs[i+1..];
    assert 0 <= j-1 < |tail|;
    assert xs == xs[..i] + [xs[i]] + xs[i+1..j] + [xs[j]] + xs[j+1..];
    assert tail == xs[..i] + xs[i+1..j] + [xs[j]] + xs[j+1..];
    assert tail[j-1] == xs[j];
    assert tail[..j-1] == xs[..i] + xs[i+1..j];
    assert tail[j..] == xs[j+1..];
    var second := Shift.MoveToFront(tail, j-1);
    var ys := [first[0]] + second;
    assert ys == [xs[i], xs[j]] + xs[..i] + xs[i+1..j] + xs[j+1..];
    assert multiset(ys) == multiset(first);
    ys
    // END MODEL BODY
  }
}
