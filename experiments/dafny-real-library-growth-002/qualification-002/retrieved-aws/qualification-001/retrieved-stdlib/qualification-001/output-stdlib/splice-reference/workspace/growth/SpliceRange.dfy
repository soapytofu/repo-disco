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
    var sourceStart := position + deleteCount;
    var suffixCount := originalSize - sourceStart;
    var replacementSize := |replacement|;
    var targetSize := originalSize - deleteCount + replacementSize;
    if deleteCount < replacementSize {
      var growth := replacementSize - deleteCount;
      Append.AppendAll(a, replacement[..growth]);
      assert a.size == targetSize;
      var remaining := suffixCount;
      while remaining > 0
        invariant a.Valid?()
        invariant a.size == targetSize == |a.items|
        invariant remaining <= suffixCount
        invariant sourceStart + suffixCount == originalSize == |original|
        invariant a.items[..position] == original[..position]
        invariant a.items[..sourceStart + remaining] ==
                  original[..sourceStart + remaining]
        invariant a.items[position + replacementSize + remaining..] ==
                  original[sourceStart + remaining..]
        invariant fresh(a.Repr - old(a.Repr))
        decreases remaining
      {
        remaining := remaining - 1;
        var sourceIndex := sourceStart + remaining;
        var destinationIndex := position + replacementSize + remaining;
        var value := a.At(sourceIndex);
        assert value == original[sourceIndex];
        ghost var previous := a.items;
        a.Put(destinationIndex, value);
        assert a.items[..sourceStart + remaining] ==
                  previous[..sourceStart + remaining];
        assert a.items[destinationIndex..] ==
                  [value] + previous[destinationIndex + 1..];
        assert original[sourceIndex..] ==
                  [value] + original[sourceIndex + 1..];
      }
    } else {
      var done: nat := 0;
      while done < suffixCount
        invariant a.Valid?()
        invariant a.size == originalSize == |a.items|
        invariant done <= suffixCount
        invariant sourceStart + suffixCount == originalSize == |original|
        invariant a.items[..position] == original[..position]
        invariant a.items[position + replacementSize..position + replacementSize + done] ==
                  original[sourceStart..sourceStart + done]
        invariant a.items[sourceStart + done..] == original[sourceStart + done..]
        invariant fresh(a.Repr - old(a.Repr))
        decreases suffixCount - done
      {
        var sourceIndex := sourceStart + done;
        var destinationIndex := position + replacementSize + done;
        var value := a.At(sourceIndex);
        assert value == original[sourceIndex];
        ghost var previous := a.items;
        a.Put(destinationIndex, value);
        assert a.items[position + replacementSize..destinationIndex + 1] ==
                  previous[position + replacementSize..destinationIndex] + [value];
        assert original[sourceStart..sourceIndex + 1] ==
                  original[sourceStart..sourceIndex] + [value];
        assert a.items[sourceIndex + 1..] == previous[sourceIndex + 1..];
        done := done + 1;
      }
    }
    assert targetSize == position + replacementSize + suffixCount;
    assert a.items[..position] == original[..position];
    assert a.items[position + replacementSize..targetSize] == original[sourceStart..];
    var workingSize := a.size;
    var index: nat := 0;
    while index < replacementSize
      invariant a.Valid?()
      invariant a.size == workingSize == |a.items|
      invariant targetSize <= workingSize
      invariant index <= replacementSize
      invariant a.items[..position] == original[..position]
      invariant a.items[position..position + index] == replacement[..index]
      invariant a.items[position + replacementSize..targetSize] == original[sourceStart..]
      invariant fresh(a.Repr - old(a.Repr))
      decreases replacementSize - index
    {
      ghost var previous := a.items;
      a.Put(position + index, replacement[index]);
      assert a.items[position..position + index + 1] ==
                previous[position..position + index] + [replacement[index]];
      assert replacement[..index + 1] == replacement[..index] + [replacement[index]];
      index := index + 1;
    }
    assert a.items[..targetSize] ==
              original[..position] + replacement + original[sourceStart..];
    while a.size > targetSize
      invariant a.Valid?()
      invariant targetSize <= a.size <= workingSize
      invariant a.size == |a.items|
      invariant a.items[..targetSize] ==
                original[..position] + replacement + original[sourceStart..]
      invariant fresh(a.Repr - old(a.Repr))
      decreases a.size - targetSize
    {
      a.PopFast();
    }
    // END REPLACEMENT
  }
}
