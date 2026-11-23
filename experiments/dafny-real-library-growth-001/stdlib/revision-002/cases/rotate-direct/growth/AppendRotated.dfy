module RepoDiscoStdRotate {
  import DA = Std.DynamicArray
  import Append = RepoDiscoStdAppend
  export provides DA, AppendRotated

  method AppendRotated<T>(a: DA.DynamicArray<T>, values: seq<T>, pivot: nat)
      returns (start: nat, end: nat)
    requires a.Valid?()
    requires pivot <= |values|
    reads a, a.Repr
    modifies a.Repr
    ensures a.Valid?()
    ensures a.items == old(a.items) + (values[pivot..] + values[..pivot])
    ensures start == old(a.size)
    ensures end == a.size
    ensures end == start + |values|
    ensures a.capacity >= old(a.capacity)
    ensures fresh(a.Repr - old(a.Repr))
    decreases |values|
  {
    // BEGIN REPLACEMENT
    var rotated := values[pivot..] + values[..pivot];
    start := a.size;
    var i: nat := 0;
    while i < |rotated|
      invariant i <= |rotated|
      invariant |rotated| == |values|
      invariant start == old(a.size)
      invariant fresh(a.Repr - old(a.Repr))
      invariant a.Valid?()
      invariant a.items == old(a.items) + rotated[..i]
      invariant a.size == start + i
      invariant a.capacity >= old(a.capacity)
      decreases |rotated| - i
    {
      assert rotated[..i + 1] == rotated[..i] + [rotated[i]];
      a.Push(rotated[i]);
      i := i + 1;
    }
    end := a.size;
    // END REPLACEMENT
  }
}
