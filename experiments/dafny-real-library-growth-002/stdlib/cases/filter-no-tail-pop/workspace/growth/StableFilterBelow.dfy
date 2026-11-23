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
    reads a, a.Repr
    modifies a.Repr
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
    var read: nat := 0;
    var write: nat := 0;
    while read < originalSize
      invariant a.Valid?()
      invariant a.size == originalSize == |a.items|
      invariant originalSize == |original|
      invariant write <= read <= originalSize
      invariant a.items[..write] == KeepBelow(original[..read], limit)
      invariant a.items[read..] == original[read..]
      invariant fresh(a.Repr - old(a.Repr))
      decreases originalSize - read
    {
      var value := a.At(read);
      assert value == original[read];
      assert original[..read + 1][..read] == original[..read];
      assert original[..read + 1][read] == value;
      assert KeepBelow(original[..read + 1], limit) ==
        KeepBelow(original[..read], limit) + (if value < limit then [value] else []);
      if value < limit {
        ghost var previous := a.items;
        a.Put(write, value);
        assert a.items == previous[write := value];
        assert a.items[..write + 1] == previous[..write] + [value];
        assert a.items[read + 1..] == previous[read + 1..];
        write := write + 1;
      }
      read := read + 1;
    }
    assert a.items[..write] == KeepBelow(original, limit);
    while a.size > originalSize
      invariant a.Valid?()
      invariant write <= a.size <= originalSize
      invariant a.size == |a.items|
      invariant a.items[..write] == KeepBelow(original, limit)
      invariant fresh(a.Repr - old(a.Repr))
      decreases a.size - write
    {
      a.PopFast();
    }
    removed := originalSize - write;
    // END REPLACEMENT
  }
}
