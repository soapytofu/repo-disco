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
    var sourceStart: nat := position + deleteCount;
    var suffixCount: nat := originalSize - sourceStart;
    var replacementSize: nat := |replacement|;
    var targetSize: nat := originalSize - deleteCount + replacementSize;
    assert position <= sourceStart <= originalSize == |original|;
    assert targetSize == position + replacementSize + suffixCount;
    if deleteCount < replacementSize {
      var growth: nat := replacementSize - deleteCount;
      Append.AppendAll(a, replacement[..growth]);
      assert a.size == targetSize;
      var remaining: nat := suffixCount;
      label ShiftStart:
      while remaining > 0
        modifies a, a.Repr
        invariant fresh@ShiftStart(a.Repr - old@ShiftStart(a.Repr))
        invariant fresh(a.Repr - old(a.Repr))
        invariant a.Valid?()
        invariant a.size == targetSize == |a.items|
        invariant 0 <= remaining <= suffixCount
        invariant position <= sourceStart <= originalSize <= targetSize
        invariant targetSize == position + replacementSize + suffixCount
        invariant sourceStart + suffixCount == originalSize == |original|
        invariant sourceStart + remaining <= originalSize
        invariant position + replacementSize + remaining <= a.size
        invariant a.items[..position] == original[..position]
        invariant a.items[..sourceStart + remaining] ==
                  original[..sourceStart + remaining]
        invariant a.items[position + replacementSize + remaining..] ==
                  original[sourceStart + remaining..]
        decreases remaining
      {
        remaining := remaining - 1;
        var sourceIndex := sourceStart + remaining;
        var destinationIndex := position + replacementSize + remaining;
        var value := a.At(sourceIndex);
        assert value == original[sourceIndex];
        ghost var previous := a.items;
        assert previous[destinationIndex + 1..] == original[sourceIndex + 1..];
        a.Put(destinationIndex, value);
        assert a.items == previous[destinationIndex := value];
        assert a.items[..position] == previous[..position];
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
        modifies a, a.Repr
        invariant fresh(a.Repr - old(a.Repr))
        invariant a.Valid?()
        invariant a.size == originalSize == |a.items|
        invariant 0 <= done <= suffixCount
        invariant position <= sourceStart <= originalSize
        invariant position + replacementSize <= sourceStart
        invariant targetSize == position + replacementSize + suffixCount <= originalSize
        invariant sourceStart + suffixCount == originalSize == |original|
        invariant a.items[..position] == original[..position]
        invariant a.items[position + replacementSize..position + replacementSize + done] ==
                  original[sourceStart..sourceStart + done]
        invariant a.items[sourceStart + done..] == original[sourceStart + done..]
        decreases suffixCount - done
      {
        var sourceIndex := sourceStart + done;
        var destinationIndex := position + replacementSize + done;
        var value := a.At(sourceIndex);
        assert value == original[sourceIndex];
        ghost var previous := a.items;
        a.Put(destinationIndex, value);
        assert a.items == previous[destinationIndex := value];
        assert a.items[..position] == previous[..position];
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
    var workingSize: nat := a.size;
    assert position + replacementSize <= targetSize <= workingSize;
    var index: nat := 0;
    while index < replacementSize
      modifies a, a.Repr
      invariant fresh(a.Repr - old(a.Repr))
      invariant a.Valid?()
      invariant a.size == workingSize == |a.items|
      invariant position + replacementSize <= targetSize <= workingSize
      invariant index <= replacementSize
      invariant a.items[..position] == original[..position]
      invariant a.items[position..position + index] == replacement[..index]
      invariant a.items[position + replacementSize..targetSize] == original[sourceStart..]
      decreases replacementSize - index
    {
      ghost var previous := a.items;
      a.Put(position + index, replacement[index]);
      assert a.items[..position] == previous[..position];
      assert a.items[position + replacementSize..targetSize] ==
                previous[position + replacementSize..targetSize];
      assert a.items[position..position + index + 1] ==
                previous[position..position + index] + [replacement[index]];
      assert replacement[..index + 1] == replacement[..index] + [replacement[index]];
      index := index + 1;
    }
    assert index == replacementSize;
    assert replacement[..index] == replacement;
    assert a.items[position..position + replacementSize] == replacement;
    assert a.items[..position + replacementSize] ==
              a.items[..position] + a.items[position..position + replacementSize];
    assert a.items[..targetSize] ==
              a.items[..position + replacementSize] +
              a.items[position + replacementSize..targetSize];
    assert a.items[..targetSize] ==
              original[..position] + replacement + original[sourceStart..];
    while a.size > targetSize
      modifies a, a.Repr
      invariant fresh(a.Repr - old(a.Repr))
      invariant a.Valid?()
      invariant targetSize <= a.size <= workingSize
      invariant a.size == |a.items|
      invariant a.items[..targetSize] ==
                original[..position] + replacement + original[sourceStart..]
      decreases a.size - targetSize
    {
      ghost var previous := a.items;
      a.PopFast();
      assert a.items[..targetSize] == previous[..targetSize];
    }
    // END REPLACEMENT
  }
}
