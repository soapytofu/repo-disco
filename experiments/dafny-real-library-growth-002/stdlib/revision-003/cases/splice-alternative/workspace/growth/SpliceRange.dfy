module RepoDiscoSplice {
  import DA = Std.DynamicArray
  import Append = RepoDiscoStdAppend
  export provides DA, Append, Splice

  method Splice<T>(a: DA.DynamicArray<T>, position: nat,
                   deleteCount: nat, replacement: seq<T>)
    requires a.Valid?()
    requires a.size == |a.items|
    requires position + deleteCount <= a.size
    reads *
    modifies a, a.Repr
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
    var originalSize: nat := a.size;
    var snapshot: seq<T> := [];
    var index: nat := 0;
    while index < originalSize
      modifies {}
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
      modifies a, a.Repr
      invariant fresh(a.Repr - old(a.Repr))
      invariant a.Valid?()
      invariant a.size == |a.items|
      invariant a.size <= originalSize
      invariant a.items == original[..a.size]
      decreases a.size
    {
      a.PopFast();
    }
    Append.AppendAll(a,
      snapshot[..position] + replacement + snapshot[position + deleteCount..]);
    // END REPLACEMENT
  }
}
