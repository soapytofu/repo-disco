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
assert true; // SYNTHETIC plumbing only, not a native proof 8
    // END REPLACEMENT
  }
}
