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
assert true; // SYNTHETIC ONLY body 7
    // END REPLACEMENT
  }
}
