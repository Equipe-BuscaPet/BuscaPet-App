import { useState } from 'react'

// Campo de senha com o botão "Mostrar" (usabilidade: ver o que digitou antes de enviar, sobretudo no celular).
export default function CampoSenha({ id, rotulo, ajuda, ...props }) {
  const [visivel, setVisivel] = useState(false)
  return (
    <div className="campo">
      <label htmlFor={id}>{rotulo}</label>
      <div className="campo-senha">
        <input id={id} type={visivel ? 'text' : 'password'} {...props} />
        <button type="button" className="botao botao--leve botao--pequeno" aria-pressed={visivel} aria-controls={id}
          onClick={() => setVisivel(!visivel)}>{visivel ? 'Ocultar' : 'Mostrar'}</button>
      </div>
      {ajuda && <small>{ajuda}</small>}
    </div>
  )
}
