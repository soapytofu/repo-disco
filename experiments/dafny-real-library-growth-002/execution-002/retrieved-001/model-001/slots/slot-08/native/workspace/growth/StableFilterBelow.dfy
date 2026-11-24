module RepoDiscoStableFilter {
  import DA = Std.DynamicArray
  export
    reveals KeepBelow
    provides DA, StableFilterBelow

  function KeepBelow(xs: seq<int>, limit: int): seq<int>
    ensures |KeepBelow(xs, limit)| <= |xs|
    decreases |xs|
  {
    if |xs| == 0 then []
    else KeepBelow(xs[..|xs| - 1], limit) +
         (if xs[|xs| - 1] < limit then [xs[|xs| - 1]] else [])
  }

  method StableFilterBelow(a: DA.DynamicArray<int>, limit: int)
      returns (removed: nat)
    requires a.Valid?()
    requires a.size == |a.items|
    reads *
    modifies a, a.Repr
    ensures a.Valid?()
    ensures a.size == |a.items|
    ensures a.items == KeepBelow(old(a.items), limit)
    ensures removed + a.size == old(a.size)
    ensures fresh(a.Repr - old(a.Repr))
    decreases a.size
  {
    // BEGIN REPLACEMENT
var oldItems := a.items;
var n := a.size;
var kept: seq<int> := [];
var i := 0;
var w := 0;

while i < n
  invariant 0 <= i <= n
  invariant 0 <= w <= i
  invariant a.Valid?()
  invariant a.size == n
  invariant a.capacity == old(a.capacity)
  invariant a.Repr == old(a.Repr)
  invariant a.items == oldItems
  invariant kept == KeepBelow(oldItems[..i], limit)
  invariant |kept| == w
  invariant forall j :: 0 <= j < w ==> a.data[j] == kept[j]
  invariant forall j :: i <= j < n ==> a.data[j] == oldItems[j]
{
  var x := a.data[i];
  assert oldItems[..i+1] == oldItems[..i] + [oldItems[i]];
  if x < limit {
    a.data[w] := x;
    kept := kept + [x];
    w := w + 1;
  }
  i := i + 1;
}

assert oldItems[..n] == oldItems;

while a.size > w
  invariant a.Valid?()
  invariant w <= a.size <= n
  invariant a.capacity == old(a.capacity)
  invariant a.Repr == old(a.Repr)
  invariant forall j :: 0 <= j < w ==> a.data[j] == kept[j]
{
  a.PopFast();
}

assert a.size == w;
assert a.items == a.data[..w];
assert forall j :: 0 <= j < w ==> a.items[j] == kept[j];
assert a.items == kept;

removed := n - w;
    // END REPLACEMENT
  }
}
