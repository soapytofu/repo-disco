module Facts {
  export ViewA provides Total, AppendA
  export ViewB provides Total, AppendB
  function Total(s: seq<int>): int
    decreases |s|
  { if |s| == 0 then 0 else s[0] + Total(s[1..]) }
  lemma {:induction false} AppendA(s: seq<int>, t: seq<int>)
    ensures Total(s + t) == Total(s) + Total(t)
    decreases |s|
  {
    if |s| == 0 {
      assert s == [];
      assert s + t == t;
    } else {
      assert |s + t| > 0;
      assert (s + t)[0] == s[0];
      assert (s + t)[1..] == s[1..] + t;
      AppendA(s[1..], []);
      assert Total(s + t) == s[0] + Total(s[1..] + t);
      assert Total(s) == s[0] + Total(s[1..]);
    }
  }
  }
  lemma {:induction false} AppendB(s: seq<int>, t: seq<int>)
    ensures Total(s + t) == Total(s) + Total(t)
    decreases |s|
  {
    if |s| == 0 {
      assert s == [];
      assert s + t == t;
    } else {
      assert |s + t| > 0;
      assert (s + t)[0] == s[0];
      assert (s + t)[1..] == s[1..] + t;
      AppendB(s[1..], []);
      assert Total(s + t) == s[0] + Total(s[1..] + t);
      assert Total(s) == s[0] + Total(s[1..]);
    }
  }
  }
}
