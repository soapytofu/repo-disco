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
      Success(Batch([], input))
    else
      var headResult := F.ReadU16Frame(input);
      if headResult.Failure? then
        Failure(headResult.error)
      else
        var frame := headResult.value;
        assert F.HasFrame(input);
        assert frame.rest == F.FrameRest(input);
        var tailResult := ReadCountedFrames(frame.rest, count - 1);
        if tailResult.Failure? then
          Failure(tailResult.error)
        else
          var tail := tailResult.value;
          var payloads := [frame.payload] + tail.payloads;
          assert HasCountedFrames(input, count);
          assert |payloads| == count;
          assert payloads[0] == frame.payload;
          assert payloads[1..] == tail.payloads;
          assert U.HasUint16Len(frame.payload);
          assert BoundedPayloads(payloads);
          assert EncodeFrames(payloads) ==
            U.UInt16ToSeq(|frame.payload| as U.uint16) + frame.payload + EncodeFrames(tail.payloads);
          assert input == U.UInt16ToSeq(|frame.payload| as U.uint16) + frame.payload + frame.rest;
          assert frame.rest == EncodeFrames(tail.payloads) + tail.rest;
          assert input == EncodeFrames(payloads) + tail.rest;
          assert tail.rest == input[|EncodeFrames(payloads)|..];
          Success(Batch(payloads, []))
    // END REPLACEMENT
  }
}
