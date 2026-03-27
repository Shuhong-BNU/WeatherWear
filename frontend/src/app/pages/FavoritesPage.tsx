import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useWeatherWearSession } from "../state/WeatherWearSession";

export default function FavoritesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { favorites, favoritesLoading, removeFavorite, runFavoriteQuery } = useWeatherWearSession();

  if (favoritesLoading) {
    return <div className="panel p-6 text-sm leading-7 text-slate-500">{t("common.loading")}</div>;
  }

  return (
    <section className="grid gap-4">
      {favorites.length ? (
        favorites.map((favorite) => (
          <div key={favorite.id} className="panel flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-lg font-semibold text-slate-950">{favorite.label}</div>
              <div className="mt-2 text-sm text-slate-500">
                {favorite.lat.toFixed(4)}, {favorite.lon.toFixed(4)}
              </div>
              <div className="mt-2 text-sm text-slate-500">
                {t("favorites.addedAt")}: {new Date(favorite.added_at).toLocaleString()}
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                className="primary-button"
                onClick={() => {
                  runFavoriteQuery(favorite);
                  navigate("/query");
                }}
              >
                {t("favorites.useFavorite")}
              </button>
              <button type="button" className="secondary-button" onClick={() => removeFavorite(favorite.id)}>
                {t("common.remove")}
              </button>
            </div>
          </div>
        ))
      ) : (
        <div className="panel p-6 text-sm leading-7 text-slate-500">{t("favorites.empty")}</div>
      )}
    </section>
  );
}
