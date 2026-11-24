include "RepoDiscoFramePair.dfy"

module RepoDiscoTaggedFramePair {
  import U = StandardLibrary.UInt
  import F = RepoDiscoU16Frame
  import P = RepoDiscoFramePair
  import opened Wrappers

  datatype TaggedPair = TaggedPair(payload: seq<U.uint8>, companion: seq<U.uint8>, rest: seq<U.uint8>)

  predicate method IsTaggedBounded(input: seq<U.uint8>, tag: U.uint8, budget: nat) {
    P.HasFramePair(input) &&
      0 < |F.FramePayload(input)| &&
      F.FramePayload(input)[0] == tag &&
      |F.FramePayload(input)| - 1 + |F.FramePayload(F.FrameRest(input))| <= budget
  }

  function method {:opaque} ReadTaggedBoundedPair(input: seq<U.uint8>, tag: U.uint8, budget: nat)
    : (result: Result<TaggedPair, string>)
    ensures result.Success? <==> IsTaggedBounded(input, tag, budget)
    ensures result.Success? ==> result.value.payload == F.FramePayload(input)[1..]
    ensures result.Success? ==> result.value.companion == F.FramePayload(F.FrameRest(input))
    ensures result.Success? ==> result.value.rest == F.FrameRest(F.FrameRest(input))
    ensures result.Success? ==> |result.value.payload| + |result.value.companion| <= budget
    ensures result.Success? ==>
      U.HasUint16Len([tag] + result.value.payload) && U.HasUint16Len(result.value.companion)
    ensures result.Success? ==>
      input == U.UInt16ToSeq(|[tag] + result.value.payload| as U.uint16) + [tag] + result.value.payload +
               U.UInt16ToSeq(|result.value.companion| as U.uint16) + result.value.companion + result.value.rest
  {
    // BEGIN REPLACEMENT
reveal P.ReadFramePair();
reveal F.ReadU16Frame();
var pairResult := P.ReadFramePair(input);
if pairResult.Failure? then
  Failure(pairResult.error)
else
  var left := pairResult.value.left;
  var right := pairResult.value.right;
  var rest := pairResult.value.rest;
  assert P.HasFramePair(input);
  assert left == F.FramePayload(input);
  assert right == F.FramePayload(F.FrameRest(input));
  assert rest == F.FrameRest(F.FrameRest(input));
  if |left| == 0 then
    Failure("First frame payload is empty")
  else if left[0] != tag then
    Failure("Tag mismatch")
  else if |left| - 1 + |right| > budget then
    Failure("Exceeds budget")
  else
    var payload := left[1..];
    var companion := right;
    assert IsTaggedBounded(input, tag, budget);
    assert payload == F.FramePayload(input)[1..];
    assert companion == F.FramePayload(F.FrameRest(input));
    assert rest == F.FrameRest(F.FrameRest(input));
    assert |payload| + |companion| <= budget;
    assert U.HasUint16Len(left);
    assert [tag] + payload == left;
    assert U.HasUint16Len([tag] + payload);
    assert U.HasUint16Len(companion);
    assert input == U.UInt16ToSeq(|left| as U.uint16) + left +
                     U.UInt16ToSeq(|right| as U.uint16) + right + rest;
    assert left == [tag] + payload;
    assert |[tag] + payload| == |left|;
    assert input == U.UInt16ToSeq(|[tag] + payload| as U.uint16) + [tag] + payload +
                     U.UInt16ToSeq(|companion| as U.uint16) + companion + rest;
    Success(TaggedPair(payload, companion, rest))
    // END REPLACEMENT
  }
}
