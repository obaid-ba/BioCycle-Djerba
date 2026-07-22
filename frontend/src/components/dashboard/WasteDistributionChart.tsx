import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useChartColors } from "@/lib/chartColors";
import { formatKg } from "@/lib/utils";
import type { PuritySplit } from "@/types";

interface Props {
  data?: PuritySplit;
  loading?: boolean;
}

export function WasteDistributionChart({ data, loading }: Props) {
  const colors = useChartColors();

  const slices = data
    ? [
        { name: "Usable feedstock", value: data.organic_kg, fill: colors.organic },
        {
          name: "Contamination",
          value: data.contamination_kg,
          fill: colors.nonOrganic,
        },
      ]
    : [];

  const isEmpty = !loading && data && data.total_kg === 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Feedstock quality</CardTitle>
        <CardDescription>
          Digestible mass vs contamination, from AI purity scores
          {data?.organic_percentage != null &&
            ` · ${data.organic_percentage.toFixed(0)}% usable`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="mx-auto h-56 w-56 animate-pulse rounded-full bg-muted" />
        ) : isEmpty ? (
          <p className="py-20 text-center text-sm text-muted-foreground">
            No scored requests yet.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={slices}
                dataKey="value"
                nameKey="name"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                strokeWidth={2}
                stroke="hsl(var(--card))"
              >
                {slices.map((s) => (
                  <Cell key={s.name} fill={s.fill} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => formatKg(value)}
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  color: "hsl(var(--popover-foreground))",
                  fontSize: 12,
                }}
              />
              <Legend
                iconType="circle"
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
