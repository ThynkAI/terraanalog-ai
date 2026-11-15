import { describe, expect, it } from "vitest";
import { clusterArcs, type ClusterSite } from "@/lib/clusterArcs";

const s = (site_id: string, cluster: number, score: number | null, lat = 0, lon = 0): ClusterSite => ({ site_id, name: site_id, lat, lon, score, cluster });

describe("clusterArcs", () => {
  it("anchors each cluster at its highest-scoring member and links every other member to it", () => {
    const { arcs, anchors } = clusterArcs([s("A", 0, 70), s("B", 0, 90), s("C", 0, null), s("D", 1, 50)]);
    expect(anchors).toEqual({ 0: "B", 1: "D" });
    expect(arcs.map((a) => `${a.from.site_id}->${a.to.site_id}`).sort()).toEqual(["B->A", "B->C"]);
  });
  it("treats missing scores as lowest and breaks ties by id (deterministic)", () => {
    expect(clusterArcs([s("Z", 0, null), s("Y", 0, null)]).anchors[0]).toBe("Y");
    expect(clusterArcs([s("Z", 0, 60), s("Y", 0, 60)]).anchors[0]).toBe("Y");
  });
  it("produces no arcs for singleton clusters or empty input", () => {
    expect(clusterArcs([s("A", 2, 10)]).arcs).toHaveLength(0);
    expect(clusterArcs([]).arcs).toHaveLength(0);
  });
});
