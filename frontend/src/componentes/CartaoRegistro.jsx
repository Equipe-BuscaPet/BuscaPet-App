import { Link } from 'react-router-dom'
import { urlFoto } from '../api'
import { EMOJI_ESPECIE, ESPECIES, PORTES, SEXOS, textoData, textoHaQuanto, textoKm } from '../rotulos'

const nome = (especie) => (especie === 'outro' ? 'Animal' : ESPECIES[especie])

// Tudo o que muda entre "perdido" e "avistamento" fica aqui, para as telas tratarem os dois do mesmo jeito.
export const TIPOS_REGISTRO = {
  perdido: {
    caminhoApi: '/perdidos',
    caminhoTela: '/reencontro/perdidos',
    titulo: (especie) => `${nome(especie)} perdido`,
    rotuloData: 'Sumiu em',
    campoData: 'data_desaparecimento',
    etiqueta: ['Perdido', 'etiqueta--erro'],
    raioAproximadoM: 1100,
  },
  avistamento: {
    caminhoApi: '/avistamentos',
    caminhoTela: '/reencontro/avistamentos',
    titulo: (especie) => `${nome(especie)} avistado`,
    rotuloData: 'Visto em',
    campoData: 'data_avistamento',
    etiqueta: ['Avistado', 'etiqueta--atencao'],
    raioAproximadoM: 110,
  },
}

export function resumoCaracteristicas(r) {
  return [PORTES[r.porte], r.cor_predominante, r.sexo !== 'indefinido' && SEXOS[r.sexo]].filter(Boolean).join(' · ')
}

export default function CartaoRegistro({ registro, tipo, acoes }) {
  const t = TIPOS_REGISTRO[tipo]
  const [rotuloEtiqueta, classeEtiqueta] = t.etiqueta
  return (
    <article className="animal registro">
      <Link to={`${t.caminhoTela}/${registro.id}`} className="registro__link">
        {registro.fotos[0] ? (
          <img className="animal__foto animal__foto--img" src={urlFoto(registro.fotos[0])} alt="" loading="lazy" />
        ) : (
          <div className="animal__foto" aria-hidden="true">{EMOJI_ESPECIE[registro.especie]}</div>
        )}
        <div className="registro__topo">
          <h3>{t.titulo(registro.especie)}</h3>
          {registro.resolvido ? (
            <span className="etiqueta etiqueta--ok">Resolvido</span>
          ) : (
            <span className={`etiqueta ${classeEtiqueta}`}>{rotuloEtiqueta}</span>
          )}
        </div>
        <p>{resumoCaracteristicas(registro)}</p>
        <p>
          {t.rotuloData} {textoData(registro[t.campoData])}
          {registro.distancia_km != null && <> · <strong>a {textoKm(registro.distancia_km)}</strong></>}
        </p>
        <p><small>Publicado {textoHaQuanto(registro.criado_em)}</small></p>
      </Link>
      {acoes && <div className="acoes registro__acoes">{acoes}</div>}
    </article>
  )
}
