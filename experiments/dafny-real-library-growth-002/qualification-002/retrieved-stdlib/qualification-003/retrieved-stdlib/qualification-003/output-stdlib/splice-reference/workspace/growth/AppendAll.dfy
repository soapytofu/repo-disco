module RepoDiscoStdAppend {
  import DA = Std.DynamicArray
  export provides DA, AppendAll

  method AppendAll<T>(a: DA.DynamicArray<T>, values: seq<T>)
    requires a.Valid?()
    reads a, a.Repr
    modifies a.Repr
    ensures a.Valid?()
    ensures a.items == old(a.items) + values
    ensures a.size == old(a.size) + |values|
    ensures a.capacity >= old(a.capacity)
    ensures fresh(a.Repr - old(a.Repr))
    decreases |values|
  {
    // BEGIN REPLACEMENT
    if |values| == 0 {
      return;
    }
    a.Push(values[0]);
    AppendAll(a, values[1..]);
  
    // END REPLACEMENT
  }
}
