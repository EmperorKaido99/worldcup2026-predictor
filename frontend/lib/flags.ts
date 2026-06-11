const FLAGS: Record<string, string> = {
  ARG: "\u{1F1E6}\u{1F1F7}", ALB: "\u{1F1E6}\u{1F1F1}", AUS: "\u{1F1E6}\u{1F1FA}",
  AUT: "\u{1F1E6}\u{1F1F9}", BEL: "\u{1F1E7}\u{1F1EA}", BOL: "\u{1F1E7}\u{1F1F4}",
  BRA: "\u{1F1E7}\u{1F1F7}", CMR: "\u{1F1E8}\u{1F1F2}", CAN: "\u{1F1E8}\u{1F1E6}",
  CHI: "\u{1F1E8}\u{1F1F1}", COL: "\u{1F1E8}\u{1F1F4}", CRC: "\u{1F1E8}\u{1F1F7}",
  CRO: "\u{1F1ED}\u{1F1F7}", DEN: "\u{1F1E9}\u{1F1F0}", ECU: "\u{1F1EA}\u{1F1E8}",
  EGY: "\u{1F1EA}\u{1F1EC}", ENG: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}",
  ESP: "\u{1F1EA}\u{1F1F8}", FRA: "\u{1F1EB}\u{1F1F7}", GER: "\u{1F1E9}\u{1F1EA}",
  HON: "\u{1F1ED}\u{1F1F3}", IDN: "\u{1F1EE}\u{1F1E9}", IRN: "\u{1F1EE}\u{1F1F7}",
  IRQ: "\u{1F1EE}\u{1F1F6}", ITA: "\u{1F1EE}\u{1F1F9}", JAM: "\u{1F1EF}\u{1F1F2}",
  JPN: "\u{1F1EF}\u{1F1F5}", KOR: "\u{1F1F0}\u{1F1F7}", KSA: "\u{1F1F8}\u{1F1E6}",
  MAR: "\u{1F1F2}\u{1F1E6}", MEX: "\u{1F1F2}\u{1F1FD}", MLI: "\u{1F1F2}\u{1F1F1}",
  NED: "\u{1F1F3}\u{1F1F1}", NGA: "\u{1F1F3}\u{1F1EC}", NZL: "\u{1F1F3}\u{1F1FF}",
  PAN: "\u{1F1F5}\u{1F1E6}", PAR: "\u{1F1F5}\u{1F1FE}", PER: "\u{1F1F5}\u{1F1EA}",
  POR: "\u{1F1F5}\u{1F1F9}", QAT: "\u{1F1F6}\u{1F1E6}", RSA: "\u{1F1FF}\u{1F1E6}",
  SCO: "\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}",
  SEN: "\u{1F1F8}\u{1F1F3}", SRB: "\u{1F1F7}\u{1F1F8}", SUI: "\u{1F1E8}\u{1F1ED}",
  SVN: "\u{1F1F8}\u{1F1EE}", TUN: "\u{1F1F9}\u{1F1F3}", TUR: "\u{1F1F9}\u{1F1F7}",
  URU: "\u{1F1FA}\u{1F1FE}", USA: "\u{1F1FA}\u{1F1F8}", UZB: "\u{1F1FA}\u{1F1FF}",
  VEN: "\u{1F1FB}\u{1F1EA}",
  // WC2026 additions
  CZE: "\u{1F1E8}\u{1F1FF}", BIH: "\u{1F1E7}\u{1F1E6}", HAI: "\u{1F1ED}\u{1F1F9}",
  CUW: "\u{1F1E8}\u{1F1FC}", CIV: "\u{1F1E8}\u{1F1EE}", SWE: "\u{1F1F8}\u{1F1EA}",
  CPV: "\u{1F1E8}\u{1F1FB}", NOR: "\u{1F1F3}\u{1F1F4}", ALG: "\u{1F1E9}\u{1F1FF}",
  JOR: "\u{1F1EF}\u{1F1F4}", COD: "\u{1F1E8}\u{1F1E9}", GHA: "\u{1F1EC}\u{1F1ED}",
};

export function getFlag(teamId: string): string {
  return FLAGS[teamId] || "\u{1F3F3}\u{FE0F}";
}
