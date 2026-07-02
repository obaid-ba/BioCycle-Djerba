import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
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
import type { TimeseriesBucket, TimeseriesGranularity } from "@/types";

interface Props {
  data?: TimeseriesBucket[];
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
    organic: b.organic_kg,
    nonOrganic: b.non_organic_kg,
  }));

  const isEmpty = !loading && chartData.length === 0;

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
            <BarChart data={chartData} barGap={2}>
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
              <YAxis
                tick={{ fill: colors.axis, fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={44}
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }}
                formatter={(value: number) => formatKg(value)}
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
                dataKey="organic"
                name="Organic"
                stackId="waste"
                fill={colors.organic}
                radius={[0, 0, 0, 0]}
              />
              <Bar
                dataKey="nonOrganic"
                name="Non-organic"
                stackId="waste"
                fill={colors.nonOrganic}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
