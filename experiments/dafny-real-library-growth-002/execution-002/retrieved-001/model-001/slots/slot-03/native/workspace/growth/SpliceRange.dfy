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
ghost var oldSize := a.size;
ghost var oldRepr := a.Repr;

var prefix := oldItems[..position];
var suffix := oldItems[position + deleteCount..];

// Pop all elements from the array
while a.size > 0
  invariant a.Valid?()
  invariant a.items == oldItems[..a.size]
  invariant a.Repr == oldRepr
  decreases a.size
{
  a.PopFast();
}

assert a.items == [];
assert a.size == 0;

// Now push prefix
Append.AppendAll(a, prefix);

assert a.items == prefix;
assert a.size == |prefix|;

// Now push replacement
Append.AppendAll(a, replacement);

assert a.items == prefix + replacement;
assert a.size == |prefix| + |replacement|;

// Now push suffix
Append.AppendAll(a, suffix);

assert a.items == prefix + replacement + suffix;
assert prefix == oldItems[..position];
assert suffix == oldItems[position + deleteCount..];
    // END REPLACEMENT
  }
}
