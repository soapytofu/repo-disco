include "RepoDiscoU16Frame.dfy"

module RepoDiscoFramePair {
  import U = StandardLibrary.UInt
  import F = RepoDiscoU16Frame
  import opened Wrappers

  datatype Pair = Pair(left: seq<U.uint8>, right: seq<U.uint8>, rest: seq<U.uint8>)

  predicate method HasFramePair(input: seq<U.uint8>) {
    F.HasFrame(input) && F.HasFrame(F.FrameRest(input))
  }

  function method {:opaque} ReadFramePair(input: seq<U.uint8>)
    : (result: Result<Pair, string>)
    ensures result.Success? <==> HasFramePair(input)
    ensures result.Success? ==> result.value.left == F.FramePayload(input)
    ensures result.Success? ==> result.value.right == F.FramePayload(F.FrameRest(input))
    ensures result.Success? ==> result.value.rest == F.FrameRest(F.FrameRest(input))
    ensures result.Success? ==>
      U.HasUint16Len(result.value.left) && U.HasUint16Len(result.value.right)
    ensures result.Success? ==>
      input == U.UInt16ToSeq(|result.value.left| as U.uint16) + result.value.left +
               U.UInt16ToSeq(|result.value.right| as U.uint16) + result.value.right +
               result.value.rest
  {
    // BEGIN REPLACEMENT

    reveal F.ReadU16Frame();
    var firstResult := F.ReadU16Frame(input);
    if firstResult.Failure? then
      Failure(firstResult.error)
    else
      var firstFrame := firstResult.value;
      var secondResult := F.ReadU16Frame(firstFrame.rest);
      if secondResult.Failure? then
        Failure(secondResult.error)
      else
        var secondFrame := secondResult.value;
        assert F.HasFrame(input);
        assert F.HasFrame(F.FrameRest(input));
        assert HasFramePair(input);
        var left := firstFrame.payload;
        var right := secondFrame.payload;
        var rest := secondFrame.rest;
        assert left == F.FramePayload(input);
        assert firstFrame.rest == F.FrameRest(input);
        assert right == F.FramePayload(F.FrameRest(input));
        assert rest == F.FrameRest(F.FrameRest(input));
        assert U.HasUint16Len(left);
        assert U.HasUint16Len(right);
        assert input == U.UInt16ToSeq(|left| as U.uint16) + left + firstFrame.rest;
        assert firstFrame.rest == U.UInt16ToSeq(|right| as U.uint16) + right + rest;
        assert input == U.UInt16ToSeq(|left| as U.uint16) + left +
                         U.UInt16ToSeq(|right| as U.uint16) + right + rest;
        Success(Pair(left, right, rest))
  
    // END REPLACEMENT
  }
}
