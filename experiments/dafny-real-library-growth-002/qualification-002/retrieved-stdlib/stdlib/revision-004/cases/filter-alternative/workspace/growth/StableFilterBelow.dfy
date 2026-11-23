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
    ghost var original := a.items;
    var originalSize := a.size;
    if originalSize == 0 {
      removed := 0;
    } else {
      var last := a.At(originalSize - 1);
      assert last == original[originalSize - 1];
      a.PopFast();
      assert a.items == original[..originalSize - 1];
      removed := StableFilterBelow(a, limit);
      if last < limit {
        a.Push(last);
      } else {
        removed := removed + 1;
      }
      assert KeepBelow(original, limit) ==
        KeepBelow(original[..originalSize - 1], limit) +
        (if last < limit then [last] else []);
    }
    // END REPLACEMENT
  }
}
