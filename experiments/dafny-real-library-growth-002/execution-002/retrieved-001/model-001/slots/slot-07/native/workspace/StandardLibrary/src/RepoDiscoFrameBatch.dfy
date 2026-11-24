include "RepoDiscoU16Frame.dfy"

module RepoDiscoFrameBatch {
  import U = StandardLibrary.UInt
  import F = RepoDiscoU16Frame
  import opened Wrappers

  datatype Batch = Batch(payloads: seq<seq<U.uint8>>, rest: seq<U.uint8>)

  predicate method HasCountedFrames(input: seq<U.uint8>, count: nat)
    decreases count
  {
    count == 0 ||
      (F.HasFrame(input) && HasCountedFrames(F.FrameRest(input), count - 1))
  }

  predicate method BoundedPayloads(payloads: seq<seq<U.uint8>>)
    decreases |payloads|
  {
    |payloads| == 0 ||
      (U.HasUint16Len(payloads[0]) && BoundedPayloads(payloads[1..]))
  }

  function method EncodeFrames(payloads: seq<seq<U.uint8>>): seq<U.uint8>
    requires BoundedPayloads(payloads)
    decreases |payloads|
  {
    if |payloads| == 0 then []
    else U.UInt16ToSeq(|payloads[0]| as U.uint16) + payloads[0] +
         EncodeFrames(payloads[1..])
  }

  function method {:opaque} ReadCountedFrames(input: seq<U.uint8>, count: nat)
    : (result: Result<Batch, string>)
    ensures result.Success? <==> HasCountedFrames(input, count)
    ensures result.Success? ==> |result.value.payloads| == count
    ensures result.Success? ==> BoundedPayloads(result.value.payloads)
    ensures result.Success? ==>
      input == EncodeFrames(result.value.payloads) + result.value.rest
    ensures result.Success? ==>
      result.value.rest == input[|EncodeFrames(result.value.payloads)|..]
    decreases count
  {
    // BEGIN REPLACEMENT
if count == 0 then
  assert HasCountedFrames(input, 0);
  assert BoundedPayloads([]);
  assert EncodeFrames([]) == [];
  Success(Batch([], input))
else
  reveal F.ReadU16Frame();
  var frameResult := F.ReadU16Frame(input);
  if frameResult.Failure? then
    assert !F.HasFrame(input);
    assert !HasCountedFrames(input, count);
    Failure(frameResult.error)
  else
    var payload := frameResult.value.payload;
    var afterFirst := frameResult.value.rest;
    assert F.HasFrame(input);
    assert payload == F.FramePayload(input);
    assert afterFirst == F.FrameRest(input);
    assert U.HasUint16Len(payload);
    var restResult := ReadCountedFrames(afterFirst, count - 1);
    if restResult.Failure? then
      assert !HasCountedFrames(afterFirst, count - 1);
      assert !HasCountedFrames(input, count);
      Failure(restResult.error)
    else
      var restPayloads := restResult.value.payloads;
      var rest := restResult.value.rest;
      assert HasCountedFrames(afterFirst, count - 1);
      assert |restPayloads| == count - 1;
      assert BoundedPayloads(restPayloads);
      assert afterFirst == EncodeFrames(restPayloads) + rest;
      var allPayloads := [payload] + restPayloads;
      assert |allPayloads| == count;
      assert allPayloads[0] == payload;
      assert allPayloads[1..] == restPayloads;
      assert U.HasUint16Len(allPayloads[0]);
      assert BoundedPayloads(allPayloads[1..]);
      assert BoundedPayloads(allPayloads);
      assert EncodeFrames(allPayloads) == U.UInt16ToSeq(|payload| as U.uint16) + payload + EncodeFrames(restPayloads);
      assert input == U.UInt16ToSeq(|payload| as U.uint16) + payload + afterFirst;
      assert input == U.UInt16ToSeq(|payload| as U.uint16) + payload + EncodeFrames(restPayloads) + rest;
      assert input == EncodeFrames(allPayloads) + rest;
      assert HasCountedFrames(input, count);
      Success(Batch(allPayloads, rest))
    // END REPLACEMENT
  }
}
