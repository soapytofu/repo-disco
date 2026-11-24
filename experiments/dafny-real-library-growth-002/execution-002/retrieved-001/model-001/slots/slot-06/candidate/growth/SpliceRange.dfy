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
ghost var oldItems := a.items;
var oldSize := a.size;
var suffix := a.items[position + deleteCount..];

// First, truncate to position
while a.size > position
  invariant a.Valid?()
  invariant a.size >= 0
  invariant a.size <= oldSize
  invariant a.items == oldItems[..a.size]
  invariant a.Repr == old(a.Repr)
  decreases a.size
{
  a.PopFast();
}

assert a.items == oldItems[..position];

// Now append replacement
Append.AppendAll(a, replacement);

assert a.items == oldItems[..position] + replacement;

// Now append suffix
Append.AppendAll(a, suffix);

assert a.items == oldItems[..position] + replacement + suffix;
assert suffix == oldItems[position + deleteCount..];
assert a.items == oldItems[..position] + replacement + oldItems[position + deleteCount..];
    // END REPLACEMENT
  }
}
