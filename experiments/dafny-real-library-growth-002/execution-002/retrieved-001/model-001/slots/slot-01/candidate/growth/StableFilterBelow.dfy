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
var writeIdx := 0;
ghost var kept: seq<int> := [];

var readIdx := 0;
while readIdx < n
  invariant 0 <= readIdx <= n
  invariant 0 <= writeIdx <= readIdx
  invariant a.Valid?()
  invariant a.size == n
  invariant a.capacity == old(a.capacity)
  invariant a.Repr == old(a.Repr)
  invariant a.data == old(a.data)
  invariant kept == KeepBelow(oldItems[..readIdx], limit)
  invariant |kept| == writeIdx
  invariant forall i :: 0 <= i < writeIdx ==> a.data[i] == kept[i]
  invariant forall i :: readIdx <= i < n ==> a.data[i] == oldItems[i]
{
  var elem := a.data[readIdx];
  if elem < limit {
    a.data[writeIdx] := elem;
    kept := kept + [elem];
    writeIdx := writeIdx + 1;
  }
  readIdx := readIdx + 1;
  assert oldItems[..readIdx] == oldItems[..readIdx-1] + [oldItems[readIdx-1]];
}

assert oldItems[..n] == oldItems;

while a.size > writeIdx
  invariant a.Valid?()
  invariant writeIdx <= a.size <= n
  invariant a.capacity == old(a.capacity)
  invariant a.Repr == old(a.Repr)
  invariant a.data == old(a.data)
  invariant forall i :: 0 <= i < writeIdx ==> a.data[i] == kept[i]
  invariant a.items == a.data[..a.size]
{
  a.PopFast();
}

assert a.size == writeIdx;
assert a.items == a.data[..writeIdx];
assert forall i :: 0 <= i < writeIdx ==> a.items[i] == kept[i];
assert |a.items| == |kept|;
assert a.items == kept;

removed := n - writeIdx;
    // END REPLACEMENT
  }
}
