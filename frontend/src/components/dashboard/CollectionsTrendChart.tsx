import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useChartColors } from "@/lib/chartColors";
import { formatKg } from "@/lib/utils";
import type { RequestTimeseriesBucket, TimeseriesGranularity } from "@/types";

interface Props {
  data?: RequestTimeseriesBucket[];
  loading?: boolean;
  granularity: TimeseriesGranularity;
  onGranularityChange: (g: TimeseriesGranularity) => void;
}

function formatBucket(bucket: string, granularity: TimeseriesGranularity): string {
  const date = new Date(bucket);
  if (Number.isNaN(date.getTime())) return bucket;
  return date.toLocaleDateString(undefined, {
    month: "short",
    ...(granularity === "day" ? { day: "numeric" } : { year: "2-digit" }),
  });
}

export function CollectionsTrendChart({
  data,
  loading,
  granularity,
  onGranularityChange,
}: Props) {
  const colors = useChartColors();

  const chartData = (data ?? []).map((b) => ({
    label: formatBucket(b.bucket, granularity),
    weight: b.declared_weight_kg,
    methane: b.estimated_methane_m3,
  }));

  // A period with buckets but no activity is still "no data" to a viewer.
  const isEmpty =
    !loading &&
    (chartData.length === 0 || chartData.every((d) => d.weight === 0));

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>Collections trend</CardTitle>
        <div className="flex gap-1">
          {(["day", "month"] as const).map((g) => (
            <Button
              key={g}
              variant={granularity === g ? "secondary" : "ghost"}
              size="sm"
              onClick={() => onGranularityChange(g)}
            >
              {g === "day" ? "Daily" : "Monthly"}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-64 w-full animate-pulse rounded bg-muted" />
        ) : isEmpty ? (
          <p className="py-24 text-center text-sm text-muted-foreground">
            No collections in this period.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={chartData} barGap={2}>
              <CartesianGrid
                vertical={false}
                stroke={colors.grid}
                strokeDasharray="3 3"
              />
              <XAxis
                dataKey="label"
                tick={{ fill: colors.axis, fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: colors.grid }}
              />
              {/* Weight and methane differ by an order of magnitude, so the
                  methane line gets its own right-hand scale. */}
              <YAxis
                yAxisId="weight"
                tick={{ fill: colors.axis, fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={52}
              />
              <YAxis
                yAxisId="methane"
                orientation="right"
                tick={{ fill: colors.axis, fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={44}
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }}
                formatter={(value: number, name: string) =>
                  name === "Est. methane"
                    ? `${value.toLocaleString(undefined, { maximumFractionDigits: 0 })} m³`
                    : formatKg(value)
                }
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  color: "hsl(var(--popover-foreground))",
                  fontSize: 12,
                }}
              />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              <Bar
                yAxisId="weight"
                dataKey="weight"
                name="Declared waste"
                fill={colors.organic}
                radius={[4, 4, 0, 0]}
              />
              <Line
                yAxisId="methane"
                type="monotone"
                dataKey="methane"
                name="Est. methane"
                stroke={colors.nonOrganic}
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
