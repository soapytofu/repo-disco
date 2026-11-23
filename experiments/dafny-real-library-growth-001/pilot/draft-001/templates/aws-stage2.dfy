include "../Model/AwsCryptographyMaterialProvidersTypes.dfy"
include "../../../../StandardLibrary/src/RepoDiscoU16Frame.dfy"

module RepoDiscoContextEntry {
  import U = StandardLibrary.UInt
  import F = RepoDiscoU16Frame
  import Types = AwsCryptographyMaterialProvidersTypes
  import UTF8
  import opened Wrappers

  datatype Entry = Entry(context: Types.EncryptionContext, rest: seq<U.uint8>)

  predicate method HasContextEntry(input: seq<U.uint8>) {
    F.HasFrame(input) &&
    F.HasFrame(F.FrameRest(input)) &&
    UTF8.ValidUTF8Seq(F.FramePayload(input)) &&
    UTF8.ValidUTF8Seq(F.FramePayload(F.FrameRest(input)))
  }

  function method {:opaque} ReadContextEntry(input: seq<U.uint8>)
    : (result: Result<Entry, string>)
    ensures result.Success? <==> HasContextEntry(input)
    ensures result.Success? ==>
      result.value.context ==
        map[F.FramePayload(input) := F.FramePayload(F.FrameRest(input))]
    ensures result.Success? ==> |result.value.context| == 1
    ensures result.Success? ==> result.value.rest == F.FrameRest(F.FrameRest(input))
  {
    // BEGIN REPLACEMENT
    // END REPLACEMENT
  }
}

