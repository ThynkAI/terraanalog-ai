/** Pure helpers for the deck.gl Analog Discovery map (unit-tested). */
export interface ClusterSite { site_id: string; name: string; lat: number; lon: number; score: number | null; cluster: number }

export function clusterArcs(sites: ClusterSite[]) {
  const by: Record<number, ClusterSite[]> = {};
  sites.forEach((s) => (by[s.cluster] ??= []).push(s));
  const arcs: { from: ClusterSite; to: ClusterSite; cluster: number }[] = [];
  const anchors: Record<number, string> = {};
  Object.entries(by).forEach(([c, members]) => {
    const anchor = [...members].sort((a, b) => (b.score ?? -1) - (a.score ?? -1) || a.site_id.localeCompare(b.site_id))[0];
    anchors[Number(c)] = anchor.site_id;
    members.filter((m) => m.site_id !== anchor.site_id).forEach((m) => arcs.push({ from: anchor, to: m, cluster: Number(c) }));
  });
  return { arcs, anchors };
}

