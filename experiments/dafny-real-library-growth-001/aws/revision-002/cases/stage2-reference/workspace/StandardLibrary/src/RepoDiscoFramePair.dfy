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
    var leftFrame := F.ReadU16Frame(input);
    if leftFrame.Failure? then
      Failure(leftFrame.error)
    else
      var rightFrame := F.ReadU16Frame(leftFrame.value.rest);
      if rightFrame.Failure? then
        Failure(rightFrame.error)
      else
        assert input == U.UInt16ToSeq(|leftFrame.value.payload| as U.uint16) +
                        leftFrame.value.payload + leftFrame.value.rest;
        assert leftFrame.value.rest == U.UInt16ToSeq(|rightFrame.value.payload| as U.uint16) +
                                       rightFrame.value.payload + rightFrame.value.rest;
        Success(Pair(leftFrame.value.payload, rightFrame.value.payload, rightFrame.value.rest))
    // END REPLACEMENT
  }
}
