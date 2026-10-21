method SumToN(n: nat) returns (s: nat)
  ensures 2 * s == n * (n + 1)
{
  s := 0;
  var i: nat := 0;
  while i < n
    invariant i <= n
    decreases n - i
  {
    i := i + 1;
    s := s + i;
  }
}
