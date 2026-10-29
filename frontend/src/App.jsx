import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  Cloud,
  RefreshCw,
  Wind,
} from "lucide-react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE || "";

function formatNumber(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "—";
  }
  return Number(value).toLocaleString("en-GB", {
    maximumFractionDigits: 1,
  });
}

function formatDate(date) {
  if (!date) return "";
  return new Date(`${date}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  });
}

async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed (${response.status}): ${path}`);
  }
  return response.json();
}

function MetricCard({ title, value, description, icon: Icon, tone = "" }) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span className="metric-title">{title}</span>
        <span className={`metric-icon ${tone}`}>
          <Icon size={19} />
        </span>
      </div>
      <div className="metric-value">{value}</div>
      <p className="metric-description">{description}</p>
    </article>
  );
}

function App() {
  const [summary, setSummary] = useState(null);
  const [daily, setDaily] = useState([]);
  const [worstDays, setWorstDays] = useState([]);
  const [bias, setBias] = useState(null);
  const [hourly, setHourly] = useState([]);
  const [selectedDate, setSelectedDate] = useState("2026-01-11");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const [summaryData, dailyData, worstData, biasData] =
          await Promise.all([
            fetchJson("/api/summary"),
            fetchJson("/api/daily-accuracy"),
            fetchJson("/api/worst-days?limit=5"),
            fetchJson("/api/forecast-bias"),
          ]);

        setSummary(summaryData);
        setDaily(dailyData.results ?? dailyData.data ?? []);
        setWorstDays(worstData.results ?? worstData.data ?? []);
        setBias(biasData);
      } catch (err) {
        setError(
          `${err.message}. Check that the FastAPI backend is running at ${API_BASE || 'the current origin'}.`,
        );
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  useEffect(() => {
    async function loadHourly() {
      try {
        const data = await fetchJson(
          `/api/hourly-comparison?start_date=${selectedDate}&end_date=${selectedDate}`,
        );
        setHourly(data.results ?? data.data ?? []); 
      } catch (err) {
        setError(err.message);
      }
    }

    loadHourly();
  }, [selectedDate]);

  const getMetric = (keys) => {
    if (!summary) return "—";
    for (const key of keys) {
      if (summary[key] !== undefined && summary[key] !== null) {
        return summary[key];
      }
    }
    return null;
  };

 const getBiasValue = () => {
  if (bias === null) return null;

  if (typeof bias === "number") return bias;

  return (
    bias.mean_forecast_bias ??
    bias.forecast_bias ??
    bias.bias ??
    bias.mean_bias ??
    bias.overall_bias ??
    null
  );
};

  const biasValue = getBiasValue();
  const biasIsPositive = Number(biasValue) >= 0;

  const dailyChartData = daily.map((item) => ({
    ...item,
    chartDate: formatDate(item.date ?? item.delivery_date ?? item.day),
    mae: Number(item.mae ?? item.MAE ?? item.mean_absolute_error ?? 0),
  }));

 const hourlyChartData = hourly.map((item) => {
  const timestamp = item.timestamp ?? item.startTime;

  return {
    ...item,
    time: timestamp
      ? new Date(timestamp).toLocaleTimeString("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "UTC",
        })
      : "",
    actual: Number(
      item.actual_generation ?? item.actual ?? item.actuals ?? 0,
    ),
    forecast: Number(
      item.forecast_generation ?? item.forecast ?? item.generation ?? 0,
    ),
  };
});

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Wind size={25} />
          </div>
          <div>
            <strong>WindSight</strong>
            <span>FORECAST INTELLIGENCE</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <nav className="navigation">
          <a className="nav-item active" href="#overview">
            <BarChart3 size={18} />
            Overview
          </a>
          <a className="nav-item" href="#accuracy">
            <Activity size={18} />
            Forecast accuracy
          </a>
          <a className="nav-item" href="#risk">
            <AlertTriangle size={18} />
            Risk analysis
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="status-dot" />
          <div>
            <strong>January 2026</strong>
            <span>Historical dataset</span>
          </div>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="page-header">
          <div>
            <div className="eyebrow">RENEWABLE ENERGY ANALYTICS</div>
            <h1>Wind Forecast Intelligence</h1>
            <p className="page-subtitle">
              Understand forecast error, identify operational risk, and make
              better-informed procurement decisions.
            </p>
          </div>

          <div className="header-actions">
            <div className="period-badge">
              <CalendarDays size={16} />
              Jan 01 – Jan 31, 2026
            </div>
            <button
              className="refresh-button"
              onClick={() => window.location.reload()}
              aria-label="Refresh dashboard"
            >
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <AlertTriangle size={19} />
            <div>
              <strong>Unable to load all dashboard data</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        {loading && !summary && (
          <div className="loading-banner">
            <RefreshCw size={18} className="spin" />
            Loading forecast intelligence data…
          </div>
        )}

        <section className="metrics-grid" aria-label="Forecast KPIs">
          <MetricCard
            title="Day-ahead MAE"
            value={formatNumber(
              getMetric(["day_ahead_mae", "mae_day_ahead", "mae"]),
            )}
            description="Mean absolute forecast error"
            icon={Activity}
            tone="blue"
          />
          <MetricCard
            title="Day-ahead RMSE"
            value={formatNumber(
              getMetric(["day_ahead_rmse", "rmse_day_ahead", "rmse"]),
            )}
            description="Penalises larger errors"
            icon={BarChart3}
            tone="purple"
          />
          <MetricCard
            title="Forecast bias"
            value={
              biasValue === null
                ? "—"
                : `${biasIsPositive ? "+" : ""}${formatNumber(biasValue)}`
            }
            description={
              biasValue === null
                ? "Average forecast minus actual"
                : biasIsPositive
                  ? "Net overforecasting"
                  : "Net underforecasting"
            }
            icon={biasIsPositive ? ArrowUpRight : ArrowDownRight}
            tone="orange"
          />
          <MetricCard
            title="Day-ahead MAPE"
            value={(() => {
              const value = getMetric([
                  "mape_percent",
                   "day_ahead_mape",
                     "mape_day_ahead",
                       "mape",
                          ]);
              if (value === null || value === "—") return "—";
              return `${formatNumber(Number(value) > 1 ? value : Number(value) * 100)}%`;
            })()}
            description="Mean absolute percentage error"
            icon={CheckCircle2}
            tone="green"
          />
        </section>

        <section className="insight-banner">
          <div className="insight-icon">
            <Cloud size={23} />
          </div>
          <div className="insight-copy">
            <strong>Procurement insight</strong>
            <p>
              Day-ahead forecasts can differ materially from forecasts closer
              to delivery. Review forecast errors and bias before relying on
              a single prediction for procurement decisions.
            </p>
          </div>
          <span className="insight-tag">JANUARY ANALYSIS</span>
        </section>

        <section className="chart-grid" id="accuracy">
          <article className="panel hourly-panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">GENERATION ANALYSIS</div>
                <h2>Actual vs forecast</h2>
                <p>Hourly wind generation compared with forecasts.</p>
              </div>
              <input
                className="date-input"
                type="date"
                min="2026-01-01"
                max="2026-01-31"
                value={selectedDate}
                onChange={(event) => setSelectedDate(event.target.value)}
                aria-label="Select day to compare"
              />
            </div>

            <div className="chart-legend-note">
              <span><i className="legend-dot actual-dot" /> Actual generation</span>
              <span><i className="legend-dot forecast-dot" /> Forecast generation</span>
            </div>

            <div className="chart-container hourly-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={hourlyChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={30} interval="preserveStartEnd"/>
                  <YAxis tick={{ fontSize: 11 }} width={54} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="actual"
                    name="Actual"
                    stroke="#16866a"
                    strokeWidth={2.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="forecast"
                    name="Forecast"
                    stroke="#5378e8"
                    strokeWidth={2.5}
                    dot={false}
                    strokeDasharray="5 4"
                  />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </div>
            {!loading && hourlyChartData.length === 0 && (
              <p className="empty-state">
                No hourly comparison data was returned for this date. Check
                the API response field names.
              </p>
            )}
          </article>

          <article className="panel daily-panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">DAILY PERFORMANCE</div>
                <h2>Forecast error trend</h2>
                <p>Daily mean absolute error across January.</p>
              </div>
            </div>
            <div className="chart-container daily-chart">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dailyChartData} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="maeGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#5378e8" stopOpacity={0.28} />
                      <stop offset="95%" stopColor="#5378e8" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="chartDate" tick={{ fontSize: 10 }} interval={4} />
                  <YAxis tick={{ fontSize: 11 }} width={52} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="mae"
                    name="Daily MAE"
                    stroke="#5378e8"
                    fill="url(#maeGradient)"
                    strokeWidth={2.5}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="chart-footnote">
              Higher MAE indicates larger average forecast errors.
            </div>
          </article>
        </section>

        <section className="bottom-grid" id="risk">
          <article className="panel table-panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">OPERATIONAL RISK</div>
                <h2>Days with highest forecast error</h2>
                <p>Prioritise review of the most challenging days.</p>
              </div>
              <span className="small-count">{worstDays.length} days</span>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>DATE</th>
                    <th>MAE</th>
                    <th>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  {worstDays.map((item, index) => {
                    const date = item.date ?? item.delivery_date ?? item.day;
                    const mae = item.mae ?? item.MAE ?? item.mean_absolute_error;
                    return (
                      <tr key={date ?? index}>
                        <td className="table-date">{formatDate(date) || date || "—"}</td>
                        <td className="table-value">{formatNumber(mae)}</td>
                        <td>
                          <span className="risk-badge">
                            <span /> High error
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                  {worstDays.length === 0 && (
                    <tr>
                      <td colSpan="3" className="empty-cell">
                        {loading ? "Loading data…" : "No risk data available."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <article className="panel bias-panel">
            <div className="panel-header">
              <div>
                <div className="section-kicker">SYSTEMATIC ERROR</div>
                <h2>Forecast bias</h2>
                <p>Average forecast minus actual generation.</p>
              </div>
            </div>

            <div className="bias-visual">
              <div className={`bias-icon ${biasIsPositive ? "positive" : "negative"}`}>
                {biasIsPositive ? <ArrowUpRight size={26} /> : <ArrowDownRight size={26} />}
              </div>
              <div>
                <div className="bias-number">
                  {biasValue === null
                    ? "—"
                    : `${biasIsPositive ? "+" : ""}${formatNumber(biasValue)}`}
                </div>
                <div className="bias-caption">
                  {biasValue === null
                    ? "Bias unavailable"
                    : biasIsPositive
                      ? "Forecasts are higher than actuals on average"
                      : "Forecasts are lower than actuals on average"}
                </div>
              </div>
            </div>

            <div className="bias-scale">
              <div className="scale-labels">
                <span>Underforecast</span>
                <span>Overforecast</span>
              </div>
              <div className="scale-track">
                <span className={`scale-marker ${biasIsPositive ? "marker-positive" : "marker-negative"}`} />
              </div>
              <p>
                Bias shows the direction of error; MAE shows its average
                magnitude regardless of direction.
              </p>
            </div>
          </article>
        </section>

        <footer className="page-footer">
          <span>WindSight · Wind Forecast Intelligence</span>
          <span>
            <span className="footer-dot" /> Connected to local analytics API
          </span>
        </footer>
      </main>
    </div>
  );
}

export default App;