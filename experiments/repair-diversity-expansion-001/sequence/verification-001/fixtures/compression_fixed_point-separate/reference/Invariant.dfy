include "Kernel.dfy"
module Invariant {
  export Public provides K, OutputClean
  import K = Kernel`Internal
  lemma {:induction false} First(s: seq<int>)
    requires 0 < |s|
    ensures 0 < |K.Compress(s)| && K.Compress(s)[0] == s[0]
    decreases |s|
  {
    reveal K.Compress();
    if |s| < 2 {
      assert |s| == 1;
      assert K.Compress(s) == s;
    } else if s[0] == s[1] {
      var rest := s[1..];
      assert 0 < |rest|;
      First(rest);
      assert rest[0] == s[1];
      assert K.Compress(s) == K.Compress(rest);
    } else {
      assert K.Compress(s) == [s[0]] + K.Compress(s[1..]);
    }
  }
  lemma {:induction false} OutputClean(s: seq<int>)
    ensures K.Clean(K.Compress(s))
    decreases |s|
  {
    reveal K.Compress();
    reveal K.Clean();
    if |s| < 2 {
      assert K.Compress(s) == s;
      assert K.Clean(s);
    } else {
      var rest := s[1..];
      assert 0 < |rest|;
      assert rest[0] == s[1];
      OutputClean(rest);
      if s[0] == s[1] {
        assert K.Compress(s) == K.Compress(rest);
      } else {
        First(rest);
        var compressed := K.Compress(rest);
        assert 0 < |compressed| && compressed[0] == s[1];
        assert K.Clean(compressed);
        assert K.Compress(s) == [s[0]] + compressed;
        assert ([s[0]] + compressed)[1..] == compressed;
        assert ([s[0]] + compressed)[0] == s[0];
        assert ([s[0]] + compressed)[1] == compressed[0];
        assert K.Clean([s[0]] + compressed);
      }
      assert K.Clean(K.Compress(s));
    }
  }
}
