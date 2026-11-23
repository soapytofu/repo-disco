module RepoDiscoSplice {
  import DA = Std.DynamicArray
  import Append = RepoDiscoStdAppend
  export provides DA, Append, Splice

  method Splice<T>(a: DA.DynamicArray<T>, position: nat,
                   deleteCount: nat, replacement: seq<T>)
    requires a.Valid?()
    requires a.size == |a.items|
    requires position + deleteCount <= a.size
    reads a, a.Repr
    modifies a.Repr
    ensures a.Valid?()
    ensures a.size == |a.items|
    ensures a.items == old(a.items)[..position] + replacement +
                       old(a.items)[position + deleteCount..]
    ensures a.size == old(a.size) - deleteCount + |replacement|
    ensures fresh(a.Repr - old(a.Repr))
    decreases a.size + |replacement|
  {
    // BEGIN REPLACEMENT
    ghost var original := a.items;
    var originalSize := a.size;
    var snapshot: seq<T> := [];
    var index: nat := 0;
    while index < originalSize
      invariant a.Valid?()
      invariant a.size == originalSize == |a.items|
      invariant a.items == original
      invariant index <= originalSize
      invariant snapshot == original[..index]
      decreases originalSize - index
    {
      var value := a.At(index);
      snapshot := snapshot + [value];
      assert original[..index + 1] == original[..index] + [original[index]];
      index := index + 1;
    }
    assert snapshot == original;
    while a.size > 0
      invariant a.Valid?()
      invariant a.size == |a.items|
      invariant a.size <= originalSize
      invariant a.items == original[..a.size]
      invariant fresh(a.Repr - old(a.Repr))
      decreases a.size
    {
      a.PopFast();
    }
    Append.AppendAll(a,
      snapshot[..position] + replacement + snapshot[position + deleteCount..]);
    // END REPLACEMENT
  }
}
